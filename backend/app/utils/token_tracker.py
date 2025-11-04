"""
Token Usage & Cost Tracking Utilities
Estimates token usage and calculates costs for LLM operations.
"""

from typing import Dict, Tuple
import re


class TokenTracker:
    """
    Track token usage and estimate costs for LLM operations.
    
    Cost estimates based on GPT-4 equivalent pricing (for comparison):
    - Input: $0.03 per 1K tokens
    - Output: $0.06 per 1K tokens
    
    Note: Ollama is free, but we track "equivalent cost" for production planning.
    """
    
    # Pricing per 1K tokens (GPT-4 equivalent for cost estimation)
    INPUT_COST_PER_1K = 0.03
    OUTPUT_COST_PER_1K = 0.06
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count from text.
        
        Rule of thumb: ~4 characters per token for English text.
        More accurate than simple char count / 4 because we account for:
        - Whitespace
        - Common words
        - Punctuation
        
        Args:
            text: Input text to estimate
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Count words (better approximation than pure char count)
        words = text.split()
        
        # Average: 1 word ≈ 1.3 tokens
        # This accounts for common words being single tokens
        # and longer/technical words being multiple tokens
        token_estimate = int(len(words) * 1.3)
        
        return max(1, token_estimate)  # At least 1 token
    
    @staticmethod
    def calculate_cost(prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate estimated cost in USD.
        
        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        input_cost = (prompt_tokens / 1000) * TokenTracker.INPUT_COST_PER_1K
        output_cost = (completion_tokens / 1000) * TokenTracker.OUTPUT_COST_PER_1K
        
        total_cost = input_cost + output_cost
        
        return round(total_cost, 6)  # Round to 6 decimal places
    
    @staticmethod
    def get_tracking_data(prompt: str, response: str) -> Dict:
        """
        Get complete tracking data for a prompt-response pair.
        
        Args:
            prompt: Input prompt sent to LLM
            response: Response received from LLM
            
        Returns:
            Dictionary with tokens and cost data
        """
        prompt_tokens = TokenTracker.estimate_tokens(prompt)
        completion_tokens = TokenTracker.estimate_tokens(response)
        total_tokens = prompt_tokens + completion_tokens
        cost = TokenTracker.calculate_cost(prompt_tokens, completion_tokens)
        
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": cost,
            "cost_breakdown": {
                "input_cost": round((prompt_tokens / 1000) * TokenTracker.INPUT_COST_PER_1K, 6),
                "output_cost": round((completion_tokens / 1000) * TokenTracker.OUTPUT_COST_PER_1K, 6)
            }
        }
    
    @staticmethod
    def format_cost(cost_usd: float) -> str:
        """
        Format cost for display.
        
        Args:
            cost_usd: Cost in USD
            
        Returns:
            Formatted string (e.g., "$0.0023" or "$0.23" or "$23.45")
        """
        if cost_usd < 0.01:
            return f"${cost_usd:.4f}"
        elif cost_usd < 1:
            return f"${cost_usd:.3f}"
        else:
            return f"${cost_usd:.2f}"
    
    @staticmethod
    def format_tokens(tokens: int) -> str:
        """
        Format token count for display.
        
        Args:
            tokens: Token count
            
        Returns:
            Formatted string (e.g., "1.2K" or "1.5M")
        """
        if tokens < 1000:
            return str(tokens)
        elif tokens < 1_000_000:
            return f"{tokens / 1000:.1f}K"
        else:
            return f"{tokens / 1_000_000:.1f}M"