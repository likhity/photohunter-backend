import os
import requests
import base64
import io
from django.conf import settings
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
import logging

logger = logging.getLogger(__name__)


class PhotoValidationService:
    """Service for validating photos using AI/LLM"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",  # GPT-4 with vision capabilities
            api_key=settings.OPENAI_API_KEY,
            temperature=0.1
        )
        self.validation_threshold = 0.7  # Minimum similarity score for approval
    
    def validate_photo(self, reference_image_url, submitted_image_url, photohunt_description):
        """
        Validate a submitted photo against a reference photo using AI
        
        Args:
            reference_image_url: URL of the reference image
            submitted_image_url: URL of the submitted image
            photohunt_description: Description of what should be photographed
        
        Returns:
            dict: Validation results including similarity score, confidence, and notes
        """
        try:
            message_content = self._create_validation_prompt(
                reference_image_url,
                submitted_image_url,
                photohunt_description
            )

            response = self.llm.invoke([HumanMessage(content=message_content)])
            validation_result = self._parse_ai_response(response.content)

            validation_result.update({
                "prompt": message_content,
                "ai_response": response.content,
                "reference_image_url": reference_image_url,
                "submitted_image_url": submitted_image_url
            })
            return validation_result

        except Exception as e:
            logger.error(f"Error validating photo: {e}")
            return self._get_fallback_response(reference_image_url, submitted_image_url)
    
    def validate_photo_with_bytes(self, reference_image_url, submitted_image_bytes, photohunt_description):
        """
        Validate a submitted photo (as bytes) against a reference photo using AI
        
        Args:
            reference_image_url: URL of the reference image
            submitted_image_bytes: Bytes of the submitted image
            photohunt_description: Description of what should be photographed
        
        Returns:
            dict: Validation results including similarity score, confidence, and notes
        """
        try:
            # Convert image bytes to base64 for the LLM
            image_base64 = base64.b64encode(submitted_image_bytes).decode('utf-8')
            
            # Create the validation prompt with base64 image
            prompt = self._create_validation_prompt_with_bytes(
                reference_image_url, 
                image_base64, 
                photohunt_description
            )
            
            # Get AI response
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            # Parse the response
            validation_result = self._parse_ai_response(response.content)
            
            # Add metadata
            validation_result.update({
                'prompt': prompt,
                'ai_response': response.content,
                'reference_image_url': reference_image_url,
                'submitted_image_bytes': True  # Indicate we used bytes instead of URL
            })
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating photo with bytes: {e}")
            return self._get_fallback_response(reference_image_url, None)
    
    def _create_validation_prompt(self, reference_image_url, submitted_image_url, description):
        """Create a multimodal prompt preserving the full original instructions."""
        return [
            {
                "type": "text",
                "text": (
                    "You are an expert photo validation AI. Your task is to compare two images "
                    "and determine if they show the same subject or location.\n\n"
                    "Please analyze both images and provide a detailed comparison. Consider:\n"
                    "1. Are they showing the same subject/location?\n"
                    "2. Are the architectural features, landmarks, or key elements the same?\n"
                    "3. Is the lighting, angle, or perspective similar enough to confirm it's the same place?\n"
                    "4. Are there any obvious differences that suggest they're different locations?\n"
                )
            },
            {
                "type": "image_url",
                "image_url": {"url": reference_image_url}
            },
            {
                "type": "image_url",
                "image_url": {"url": submitted_image_url}
            },
            {
                "type": "text",
                "text": (
                    f"PHOTO HUNT DESCRIPTION: {description}\n\n"
                    "Respond in the following JSON format:\n"
                    "{\n"
                    '    "similarity_score": 0.85,  // Score from 0.0 to 1.0 (1.0 = identical)\n'
                    '    "confidence_score": 0.92,  // Your confidence in the assessment (0.0 to 1.0)\n'
                    '    "is_valid": true,          // Whether the submitted photo matches the reference\n'
                    '    "notes": "The images show the same architectural landmark with similar lighting and angle. '
                    'The key features match the description perfectly.",\n'
                    '    "key_matches": ["Gothic architecture", "Stained glass windows", "Flying buttresses"],\n'
                    '    "key_differences": ["Slight difference in lighting", "Different time of day"]\n'
                    "}\n\n"
                    "Be strict but fair in your assessment. The photo should clearly show the same subject/location as the reference image."
                )
            }
        ]
    
    def _create_validation_prompt_with_bytes(self, reference_image_url, submitted_image_base64, description):
        """Create the prompt for photo validation with base64 image"""
        return f"""
You are an expert photo validation AI. Your task is to compare two images and determine if they show the same subject or location.

REFERENCE IMAGE: {reference_image_url}
SUBMITTED IMAGE (base64): data:image/jpeg;base64,{submitted_image_base64}
PHOTO HUNT DESCRIPTION: {description}

Please analyze both images and provide a detailed comparison. Consider:
1. Are they showing the same subject/location?
2. Are the architectural features, landmarks, or key elements the same?
3. Is the lighting, angle, or perspective similar enough to confirm it's the same place?
4. Are there any obvious differences that suggest they're different locations?

Respond in the following JSON format:
{{
    "similarity_score": 0.85,  // Score from 0.0 to 1.0 (1.0 = identical)
    "confidence_score": 0.92,  // Your confidence in the assessment (0.0 to 1.0)
    "is_valid": true,          // Whether the submitted photo matches the reference
    "notes": "The images show the same architectural landmark with similar lighting and angle. The key features match the description perfectly.",
    "key_matches": ["Gothic architecture", "Stained glass windows", "Flying buttresses"],
    "key_differences": ["Slight difference in lighting", "Different time of day"]
}}

Be strict but fair in your assessment. The photo should clearly show the same subject/location as the reference image.
"""
    
    def _parse_ai_response(self, response_content):
        """Parse the AI response and extract validation data"""
        try:
            import json
            import re
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                # Validate and set defaults
                return {
                    'similarity_score': float(result.get('similarity_score', 0.0)),
                    'confidence_score': float(result.get('confidence_score', 0.0)),
                    'is_valid': bool(result.get('is_valid', False)),
                    'notes': result.get('notes', 'AI validation completed'),
                    'key_matches': result.get('key_matches', []),
                    'key_differences': result.get('key_differences', [])
                }
            else:
                # Fallback parsing if JSON extraction fails
                return self._parse_text_response(response_content)
                
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._get_fallback_response()
    
    def _parse_text_response(self, response_content):
        """Parse text response when JSON extraction fails"""
        # Look for key phrases in the response
        similarity_score = 0.5  # Default
        confidence_score = 0.5
        is_valid = False
        notes = response_content
        
        # Try to extract scores from text
        import re
        
        # Look for similarity score
        similarity_match = re.search(r'similarity[:\s]+(\d+\.?\d*)', response_content, re.IGNORECASE)
        if similarity_match:
            similarity_score = float(similarity_match.group(1))
            if similarity_score > 1.0:
                similarity_score = similarity_score / 100.0  # Convert percentage to decimal
        
        # Look for confidence score
        confidence_match = re.search(r'confidence[:\s]+(\d+\.?\d*)', response_content, re.IGNORECASE)
        if confidence_match:
            confidence_score = float(confidence_match.group(1))
            if confidence_score > 1.0:
                confidence_score = confidence_score / 100.0
        
        # Look for validation decision
        if any(word in response_content.lower() for word in ['valid', 'match', 'same', 'correct']):
            is_valid = True
        elif any(word in response_content.lower() for word in ['invalid', 'different', 'not match', 'incorrect']):
            is_valid = False
        
        return {
            'similarity_score': similarity_score,
            'confidence_score': confidence_score,
            'is_valid': is_valid,
            'notes': notes,
            'key_matches': [],
            'key_differences': []
        }
    
    def _get_fallback_response(self, reference_image_url=None, submitted_image_url=None):
        """Get fallback response when AI validation fails"""
        return {
            'similarity_score': 0.0,
            'confidence_score': 0.0,
            'is_valid': False,
            'notes': 'AI validation failed - manual review required',
            'key_matches': [],
            'key_differences': [],
            'prompt': 'Validation failed',
            'ai_response': 'AI validation service unavailable',
            'reference_image_url': reference_image_url,
            'submitted_image_url': submitted_image_url
        }
    
    def validate_with_custom_prompt(self, reference_image_url, submitted_image_url, custom_prompt):
        """
        Validate photos with a custom prompt
        
        Args:
            reference_image_url: URL of the reference image
            submitted_image_url: URL of the submitted image
            custom_prompt: Custom validation prompt
        
        Returns:
            dict: Validation results
        """
        try:
            prompt = f"""
{custom_prompt}

REFERENCE IMAGE: {reference_image_url}
SUBMITTED IMAGE: {submitted_image_url}

Please analyze both images and provide your assessment in JSON format:
{{
    "similarity_score": 0.85,
    "confidence_score": 0.92,
    "is_valid": true,
    "notes": "Your detailed analysis here"
}}
"""
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return self._parse_ai_response(response.content)
            
        except Exception as e:
            logger.error(f"Error in custom validation: {e}")
            return self._get_fallback_response(reference_image_url, submitted_image_url)
