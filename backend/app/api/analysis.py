"""
API routes for RA Medical Image Analysis
"""

from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import io

from ..models.schemas import AnalysisResponse, ReportResponse, FullAnalysisResponse
from ..services.ai_model import get_model
from ..services.gpt_service import get_gpt_service
from ..utils.fallback import apply_fallback_logic, FallbackHandler


router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze", response_model=FullAnalysisResponse)
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyze medical image for RA detection

    Args:
        file: Medical image file (JPEG, PNG, etc.)

    Returns:
        FullAnalysisResponse with analysis and report
    """

    try:
        # Validate file type
        if file.content_type not in ["image/jpeg", "image/png", "image/jpg", "image/gif"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload an image (JPEG, PNG, GIF)"
            )

        # Read file
        contents = await file.read()

        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Empty file")

        if len(contents) > 50 * 1024 * 1024:  # 50 MB limit
            raise HTTPException(status_code=413, detail="File too large (max 50 MB)")

        # Process image with AI model
        model = get_model()
        ai_result = model.process_image(contents)

        # Create analysis response
        analysis = AnalysisResponse(
            detection_image=ai_result["detection_image"],
            gradcam_image=ai_result["gradcam_image"],
            confidence_score=ai_result["confidence_score"],
            diagnosis=ai_result["diagnosis"],
            raw_scores=ai_result["raw_scores"]
        )

        # Generate clinical report using GPT
        gpt_service = get_gpt_service()
        gradcam_summary = _get_gradcam_summary(ai_result["diagnosis"], ai_result["raw_scores"])
        report_text, was_truncated, warning = gpt_service.generate_report(
            confidence_score=ai_result["confidence_score"],
            diagnosis=ai_result["diagnosis"],
            gradcam_summary=gradcam_summary
        )

        # Create report response
        report = ReportResponse(
            report=report_text,
            truncated=was_truncated,
            warning=warning
        )

        # Apply fallback logic
        full_response = FullAnalysisResponse(
            analysis=analysis,
            report=report
        )

        # Convert to dict for fallback processing
        response_dict = full_response.model_dump()

        # Apply fallback logic
        response_dict = _apply_fallback_to_response(response_dict)

        return FullAnalysisResponse(**response_dict)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@router.post("/analyze-path", response_model=FullAnalysisResponse)
async def analyze_image_path(patient_id: str, filename: str):
    """
    Analyze an image on disk using patient_id and filename.
    """
    try:
        image_root = Path(__file__).resolve().parents[3] / 'images'
        image_path = image_root / patient_id / filename
        if not image_path.exists() or not image_path.is_file():
            raise HTTPException(status_code=404, detail='Image not found')

        contents = image_path.read_bytes()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail='Empty file')

        model = get_model()
        ai_result = model.process_image(contents)

        analysis = AnalysisResponse(
            detection_image=ai_result['detection_image'],
            gradcam_image=ai_result['gradcam_image'],
            confidence_score=ai_result['confidence_score'],
            diagnosis=ai_result['diagnosis'],
            raw_scores=ai_result['raw_scores']
        )

        gpt_service = get_gpt_service()
        gradcam_summary = _get_gradcam_summary(ai_result['diagnosis'], ai_result['raw_scores'])
        report_text, was_truncated, warning = gpt_service.generate_report(
            confidence_score=ai_result['confidence_score'],
            diagnosis=ai_result['diagnosis'],
            gradcam_summary=gradcam_summary
        )

        report = ReportResponse(
            report=report_text,
            truncated=was_truncated,
            warning=warning
        )

        full_response = FullAnalysisResponse(
            analysis=analysis,
            report=report
        )

        response_dict = full_response.model_dump()
        response_dict = _apply_fallback_to_response(response_dict)

        return FullAnalysisResponse(**response_dict)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


def _get_gradcam_summary(diagnosis: str, raw_scores: Dict) -> str:
    """Generate Grad-CAM summary for GPT report generation"""
    return f"Diagnosis: {diagnosis}, Confidence scores: {raw_scores}"


def _apply_fallback_to_response(response_dict: Dict) -> Dict:
    """Apply fallback UI logic based on confidence score"""
    confidence = response_dict.get('analysis', {}).get('confidence_score', 0)

    fallback_ui_state = {
        'confidence_level': 'high' if confidence >= 0.8 else 'medium' if confidence >= 0.5 else 'low',
        'color_code': '#10b981' if confidence >= 0.8 else '#f59e0b' if confidence >= 0.5 else '#ef4444',
        'show_diagnosis': confidence >= 0.3,
        'show_warning': confidence < 0.5,
        'warning_message': None,
        'diagnosis_text': response_dict.get('analysis', {}).get('diagnosis', ''),
        'truncate_report': confidence < 0.5
    }

    if confidence < 0.5:
        fallback_ui_state['warning_message'] = "AI 결과의 신뢰도가 낮습니다. 전문의의 판단을 우선하세요."
        if confidence < 0.3:
            fallback_ui_state['diagnosis_text'] = "AI 결과 신뢰도 낮음"
            report = response_dict.get('report', {}).get('report', '')
            response_dict['report']['report'] = f"⚠️ Limited confidence analysis\n\n{report}"

    response_dict['fallback_ui_state'] = fallback_ui_state
    return response_dict


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "service": "RA Medical Image Analysis"}
    )


@router.get("/config")
async def get_config():
    """Get backend configuration and capabilities"""

    gpt_service = get_gpt_service()

    return JSONResponse(
        status_code=200,
        content={
            "model_version": "1.0.0",
            "gpt_available": gpt_service.is_available(),
            "confidence_thresholds": {
                "high": 0.8,
                "medium": 0.5,
                "low": 0.3
            },
            "color_scheme": {
                "high": "#10b981",
                "medium": "#f59e0b",
                "low": "#ef4444"
            }
        }
    )