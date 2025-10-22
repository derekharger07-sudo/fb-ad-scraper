import sys, os
from fastapi import FastAPI, Query, BackgroundTasks, Request, HTTPException, Depends, Cookie, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlmodel import select, desc
from sqlalchemy import or_, String, cast
from app.db.repo import get_session, init_db
from app.db.models import OpportunityCard, AdCreative, User
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder

# 🧠 Import the analyzer
from app.api.analyze_ad import analyze_video

# 🔐 Import authentication utilities
from app.api.auth import (
    create_user,
    authenticate_user,
    get_user_by_username,
    get_user_by_email,
    get_user_by_id,
    create_session_token,
    verify_session_token
)

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

app = FastAPI(title="Product Research Tool — Thin Slice API")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
allowed_origins = [
    FRONTEND_URL,
    "https://b753f92c-5510-4537-9c61-358b6d74bdf3-00-390tl0pzcht9z.riker.replit.dev",
    "*"  # Allow all origins for development
]
if os.environ.get("REPLIT_DEV_DOMAIN"):
    allowed_origins.append(f"https://{os.environ['REPLIT_DEV_DOMAIN']}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


async def get_current_user(session_token: Optional[str] = Cookie(None)) -> Optional[User]:
    if not session_token:
        return None
    user_id = verify_session_token(session_token)
    if not user_id:
        return None
    return get_user_by_id(user_id)


async def require_auth(current_user: Optional[User] = Depends(get_current_user)) -> User:
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return current_user


class SignupRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/signup")
async def signup(request: SignupRequest, response: Response):
    if get_user_by_username(request.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    if get_user_by_email(request.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    
    user = create_user(request.username, request.email, request.password)
    
    if not user.id:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    token = create_session_token(user.id)
    is_production = os.environ.get("REPLIT_DEPLOYMENT") == "1"
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=86400 * 7
    )
    
    return {
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }


@app.post("/api/login")
async def login(request: LoginRequest, response: Response):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not user.id:
        raise HTTPException(status_code=500, detail="Invalid user data")
    
    token = create_session_token(user.id)
    is_production = os.environ.get("REPLIT_DEPLOYMENT") == "1"
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=86400 * 7
    )
    
    return {
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }


@app.post("/api/logout")
async def logout(response: Response):
    is_production = os.environ.get("REPLIT_DEPLOYMENT") == "1"
    response.delete_cookie(
        key="session_token",
        path="/",
        samesite="lax",
        secure=is_production
    )
    return {"success": True}


@app.get("/api/user")
async def get_user(current_user: Optional[User] = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }


# Scraper endpoint
@app.post("/scrape")
async def run_scraper(background_tasks: BackgroundTasks):
    def run_scrape():
        from run_test_scraper import main as run_test_scraper
        run_test_scraper()
    background_tasks.add_task(run_scrape)
    return {"status": "Scraper started 🚀"}


class AnalyzeRequest(BaseModel):
    video_url: str
    ad_text: Optional[str] = ""


@app.post("/analyze")
async def analyze_ad(request: AnalyzeRequest):
    """
    Analyze a video ad using GPT-5 AI.
    Returns creative insights: emotions, scenes, product focus, and structure.
    """
    try:
        # Validate video URL is provided
        if not request.video_url or request.video_url.strip() == "":
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Missing video URL",
                    "message": "This ad doesn't have a video to analyze. Video URL is required."
                }
            )
        
        analysis = analyze_video(request.video_url, request.ad_text)
        return {
            "success": True,
            "analysis": analysis
        }
    except ValueError as e:
        # Handle missing API key or invalid input
        error_msg = str(e)
        if "OPENAI_API_KEY" in error_msg:
            message = "OpenAI API key not configured"
        elif "Video URL" in error_msg:
            message = "This ad doesn't have a video to analyze"
        else:
            message = error_msg
        
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": str(e),
                "message": message
            }
        )
    except Exception as e:
        # Handle other errors (network, video download, etc.)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Analysis failed - unable to process video"
            }
        )


class OpportunityCardOut(BaseModel):
    product_hash: str
    score: float
    price_band: str | None = None
    recommended_geos: List[str] | None = None
    reasons: List[str] | None = None


class AdCreativeOut(BaseModel):
    id: int
    account_name: Optional[str]
    advertiser_favicon: Optional[str]
    caption: Optional[str]
    landing_url: Optional[str]
    video_url: Optional[str]
    country: Optional[str]
    started_running_on: Optional[str]
    days_running: Optional[int]
    total_score: Optional[int]
    stars: Optional[int]
    creative_variant_count: Optional[int]
    creative_hash: Optional[str]
    monthly_visits: Optional[int]
    is_spark_ad: Optional[bool]
    advertiser_total_ads: Optional[int] = None  # Total ads count for this advertiser
    platform_type: Optional[str]
    product_name: Optional[str]
    product_price: Optional[str]
    page_type: Optional[str]
    ad_image: Optional[str] = None  # Ad creative image from raw JSON
    poster_url: Optional[str] = None  # Video poster/thumbnail from raw JSON
    is_active: Optional[bool]
    fb_delivery_status: Optional[str]
    detection_method: Optional[str]
    page_id: Optional[str]
    raw: Optional[dict]


def to_out(card: OpportunityCard) -> OpportunityCardOut:
    return OpportunityCardOut(
        product_hash=card.product_hash,
        score=card.score,
        price_band=card.price_band,
        recommended_geos=card.recommended_geos.split(",") if card.recommended_geos else None,
        reasons=card.reasons.split("\n") if card.reasons else None,
    )


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/")
def serve_frontend():
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend.html")
    return FileResponse(frontend_path)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/opportunities", response_model=List[OpportunityCardOut])
def get_opportunities():
    with get_session() as s:
        rows = s.exec(select(OpportunityCard).order_by(desc(OpportunityCard.score))).all()
        return [to_out(r) for r in rows]


@app.get("/ads", response_model=List[AdCreativeOut])
def get_ads(
    search_query: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(
        None,
        description="Filter by active status (true/false). If not provided, returns both active and inactive ads.",
    ),
    limit: int = 20,
    offset: int = 0,
):
    with get_session() as s:
        stmt = select(AdCreative)
        if search_query:
            like_pattern = f"%{search_query}%"
            stmt = stmt.where(
                or_(
                    AdCreative.search_query.ilike(like_pattern),
                    AdCreative.account_name.ilike(like_pattern),
                    AdCreative.caption.ilike(like_pattern),
                    cast(AdCreative.raw, String).ilike(like_pattern),
                )
            )
        if country:
            stmt = stmt.where(AdCreative.country == country)
        if min_score is not None:
            stmt = stmt.where((AdCreative.total_score != None) & (AdCreative.total_score >= min_score))
        if is_active is not None:
            stmt = stmt.where(AdCreative.is_active == is_active)
        stmt = stmt.order_by(desc(AdCreative.total_score)).offset(offset).limit(limit)
        rows = s.exec(stmt).all()
        
        # Get advertiser total counts for all advertisers in this batch
        advertiser_names = list(set([row.account_name for row in rows if row.account_name]))
        advertiser_counts = {}
        
        if advertiser_names:
            # Count ads per advertiser in one query
            from sqlalchemy import func
            count_stmt = (
                select(AdCreative.account_name, func.count(AdCreative.id).label("total"))
                .where(AdCreative.account_name.in_(advertiser_names))
                .group_by(AdCreative.account_name)
            )
            count_results = s.exec(count_stmt).all()
            advertiser_counts = {name: count for name, count in count_results}
        
        # Add advertiser_total_ads and creative media from raw JSON to each ad
        result = []
        for row in rows:
            ad_dict = jsonable_encoder(row)
            ad_dict["advertiser_total_ads"] = advertiser_counts.get(row.account_name, 1)
            
            # Extract ad_image and poster_url from raw JSON if available
            if row.raw and isinstance(row.raw, dict):
                ad_dict["ad_image"] = row.raw.get("ad_image")
                ad_dict["poster_url"] = row.raw.get("poster_url")
            
            result.append(ad_dict)
        
        return result


# 🧠 ---------------------------------------------------------
# 🧠  AI Analyzer Route
# ------------------------------------------------------------
@app.post("/api/analyze_ad")
async def analyze_ad(request: Request):
    """
    Runs the AI analyzer on a given ad.
    Expects: {"video_url": "...", "ad_text": "..."}
    """
    data = await request.json()
    video_url = data.get("video_url")
    ad_text = data.get("ad_text", "")

    if not video_url:
        return JSONResponse({"error": "Missing video_url"}, status_code=400)

    try:
        result = analyze_video(video_url, ad_text)
        return JSONResponse({"analysis": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
