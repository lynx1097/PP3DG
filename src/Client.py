import os
import json
import typing
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("CRITICAL: 'google-genai' library not found. Please run: pip install google-genai")

from PyQt6.QtCore import QThread, pyqtSignal

load_dotenv()

# --- DATA MODELS ---

class UIElement(BaseModel):
    label: str = Field(description="Name of the element")
    ymin: int = Field(description="Top Y (0-1000)")
    xmin: int = Field(description="Left X (0-1000)")
    ymax: int = Field(description="Bottom Y (0-1000)")
    xmax: int = Field(description="Right X (0-1000)")
    usage_instruction: str = Field(description="Step-by-step instruction")

class UIScreenAnalysis(BaseModel):
    elements: list[UIElement]

class CodeFix(BaseModel):
    fixed_code: str = Field(description="The full, corrected Python code block")
    explanation: str = Field(description="Brief explanation of the fix")

# --- KEY MANAGER ---
class KeyManager:
    def __init__(self):
        self.keys = [k for k in [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2"), os.getenv("GEMINI_API_KEY_3")] if k]
        self.current_index = 0

    def get_current_key(self):
        if not self.keys: raise ValueError("No API Keys found")
        return self.keys[self.current_index]

    def rotate_key(self):
        """Switches to the next available key. Returns True if rotated, False if only 1 key."""
        if len(self.keys) <= 1: return False
        self.current_index = (self.current_index + 1) % len(self.keys)
        print(f"[Client] Switched to API Key #{self.current_index + 1}")
        return True

# --- CLIENT ---
class GeminiClient:
    # Model Hierarchy for Fallback
    MODELS = {
        "smartest": "gemini-flash-latest",
        "moderate": "gemini-3-flash-preview",
        "backup": "gemma-3-27b-it"     # Fallback for everything
    }

    def __init__(self):
        self.key_manager = KeyManager()
        self.client = self._init_client()
        self.system_context = self._load_system_context()

    def _init_client(self):
        return genai.Client(api_key=self.key_manager.get_current_key())

    def _load_system_context(self):
        """Loads persistent system instructions from context.txt"""
        try:
            ctx_path = Path(__file__).parent / "context.txt"
            if ctx_path.exists():
                with open(ctx_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception as e:
            print(f"Warning: Could not load context.txt: {e}")
        return ""

    def generate_response(self, prompt, context="", use_case="chat", image_path=None, ref_card=None):
        # 1. Prepare Content
        full_context = ""
        if self.system_context:
            full_context += f"=== SYSTEM INSTRUCTIONS ===\n{self.system_context}\n\n"
        if ref_card:
            full_context += f"[Reference Documentation]:\n{json.dumps(ref_card, indent=2)}\n\n"
        if context:
            full_context += f"=== CURRENT CONTEXT ===\n{context}\n\n"

        config = types.GenerateContentConfig(temperature=0.7, max_output_tokens=8192)
        contents = [f"{full_context}\n\nUser Query: {prompt}"]

        if use_case == "vision":
            config.response_mime_type = "application/json"
            config.response_schema = UIScreenAnalysis
            if image_path:
                try:
                    from PIL import Image
                    contents.append(Image.open(image_path))
                except: pass
        elif use_case == "code_fix":
            config.response_mime_type = "application/json"
            config.response_schema = CodeFix

        # 2. Determine Strategy: Primary Model -> Backup Model
        model_pipeline = []
        if use_case in ["vision", "code_fix"]:
            model_pipeline = [self.MODELS["smartest"], self.MODELS["backup"]]
        else:
            model_pipeline = [self.MODELS["moderate"], self.MODELS["backup"]]

        last_error = ""

        # --- EXECUTION LOOP (Model -> Key -> Retry) ---
        for model_id in model_pipeline:
            # Try each key for the current model
            attempts_per_model = len(self.key_manager.keys)
            
            for _ in range(attempts_per_model):
                try:
                    # print(f"[Client] Attempting with Model: {model_id} | Key Index: {self.key_manager.current_index}")
                    response = self.client.models.generate_content(
                        model=model_id, contents=contents, config=config
                    )
                    
                    if use_case in ["vision", "code_fix"]:
                        return response.parsed
                    return response.text

                except Exception as e:
                    last_error = str(e)
                    print(f"[Client] Error ({model_id}): {e}")
                    
                    # Rotate Key and Re-init Client
                    if self.key_manager.rotate_key():
                        self.client = self._init_client()
                    else:
                        # If no alternate key, break inner loop to try next model
                        break
            
            print(f"[Client] All keys failed for {model_id}. Falling back to lower model...")

        return f"Error: Request failed after trying all keys and models. Last error: {last_error}"

# --- WORKER ---
class GeminiWorker(QThread):
    response_received = pyqtSignal(str)
    vision_received = pyqtSignal(object) 
    code_fix_received = pyqtSignal(object) 
    error_occurred = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, prompt, use_case="chat", image_path=None, ref_card=None):
        super().__init__()
        self.prompt = prompt
        self.use_case = use_case
        self.image_path = image_path
        self.ref_card = ref_card
        self.client = GeminiClient()

    def run(self):
        try:
            result = self.client.generate_response(
                self.prompt, use_case=self.use_case, image_path=self.image_path, ref_card=self.ref_card
            )
            
            if self.use_case == "vision":
                self.vision_received.emit(result)
            elif self.use_case == "code_fix":
                self.code_fix_received.emit(result)
            else:
                self.response_received.emit(str(result))
                
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished_signal.emit()