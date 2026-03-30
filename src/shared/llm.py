"""
NVIDIA NIM LLM Factory — Centralizes all 17+ models for LiveMirror.
Categorizes models by purpose: Reasoning, Speed, Specialized, and RAG.
"""

import os
from typing import Optional, Dict, Any
from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings
from openai import OpenAI

class LLMFactory:
    """
    Factory for retrieving specific NVIDIA NIM models based on task requirements.
    
    Tiers:
    - FRONTIER: DeepSeek v3.2 / GPT-OSS 120B (High reasoning)
    - BALANCED: Qwen 3.5 122B / Mistral Small (Production standard)
    - FLASH: Step 3.5 Flash / Phi-4 Mini (High speed, low latency)
    - SPECIALIZED: Stockmark (Finance), Sarvam (Multilingual)
    """

    @staticmethod
    def get_model(
        tier: str = "balanced", 
        streaming: bool = True, 
        temperature: float = 0.5,
        **kwargs
    ) -> ChatNVIDIA:
        """Get a ChatNVIDIA instance based on the requested performance tier."""
        api_key = os.getenv("NVIDIA_API_KEY_PRIMARY") or os.getenv("NVIDIA_API_KEY")
        
        # Model Selection Logic
        model_map = {
            "frontier": "deepseek-ai/deepseek-v3.2",
            "balanced": "qwen/qwen3.5-122b-a10b",
            "flash": "stepfun-ai/step-3.5-flash",
            "finance": "stockmark/stockmark-2-100b-instruct",
            "multilingual": "sarvamai/sarvam-m",
            "reasoning": "openai/gpt-oss-120b"
        }
        
        selected_model = model_map.get(tier, model_map["balanced"])
        
        return ChatNVIDIA(
            model=selected_model,
            nvidia_api_key=api_key,
            temperature=temperature,
            max_tokens=kwargs.get("max_tokens", 4096),
            streaming=streaming
        )

    @staticmethod
    def get_openai_client(endpoint: str = "https://integrate.api.nvidia.com/v1") -> OpenAI:
        """Returns a raw OpenAI-compatible client for low-level SDK calls."""
        return OpenAI(
            base_url=endpoint,
            api_key=os.getenv("NVIDIA_API_KEY_PRIMARY") or os.getenv("NVIDIA_API_KEY")
        )

    @staticmethod
    def get_embeddings() -> NVIDIAEmbeddings:
        """Returns NVIDIA NIM Embeddings (replaces local SentenceTransformers)."""
        return NVIDIAEmbeddings(
            model="nvidia/nv-embedqa-e5-v5", 
            nvidia_api_key=os.getenv("NVIDIA_API_KEY_PRIMARY")
        )

    @staticmethod
    def get_reranker() -> ChatNVIDIA:
        """Returns the Llama Reranker model."""
        return ChatNVIDIA(
            model="llama-nemotron-rerank-1b-v2",
            nvidia_api_key=os.getenv("NVIDIA_API_KEY_RERANK")
        )
