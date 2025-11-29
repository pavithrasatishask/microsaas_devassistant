"""Cost tracking service for Claude API usage."""
from typing import Optional
from datetime import datetime
from services.supabase_client import SupabaseClient


class CostTracker:
    """Track API costs per request."""
    
    # Haiku 4.5 Pricing (as of 2025)
    INPUT_COST_PER_MILLION = 1.0  # $1 per 1M input tokens
    OUTPUT_COST_PER_MILLION = 5.0  # $5 per 1M output tokens
    CACHED_COST_PER_MILLION = 0.1  # $0.1 per 1M cached tokens (90% discount)
    
    def __init__(self, supabase_client: Optional[SupabaseClient] = None):
        """Initialize cost tracker."""
        self.supabase = supabase_client
    
    def track_request(self, input_tokens: int, output_tokens: int, 
                     cached_tokens: int = 0) -> dict:
        """
        Track API costs per request.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached_tokens: Number of cached tokens (saved 90%)
            
        Returns:
            Dictionary with cost breakdown
        """
        input_cost = (input_tokens / 1_000_000) * self.INPUT_COST_PER_MILLION
        output_cost = (output_tokens / 1_000_000) * self.OUTPUT_COST_PER_MILLION
        cache_cost = (cached_tokens / 1_000_000) * self.CACHED_COST_PER_MILLION
        
        total_cost = input_cost + output_cost + cache_cost
        
        cost_data = {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cached_tokens': cached_tokens,
            'input_cost': input_cost,
            'output_cost': output_cost,
            'cache_cost': cache_cost,
            'total_cost': total_cost,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store in database if supabase client is available
        # Note: You may want to create a cost_tracking table in Supabase
        # For now, we'll just return the cost data
        
        return cost_data
    
    def calculate_savings(self, cached_tokens: int) -> dict:
        """
        Calculate savings from prompt caching.
        
        Args:
            cached_tokens: Number of tokens that were cached
            
        Returns:
            Dictionary with savings information
        """
        original_cost = (cached_tokens / 1_000_000) * self.INPUT_COST_PER_MILLION
        cached_cost = (cached_tokens / 1_000_000) * self.CACHED_COST_PER_MILLION
        savings = original_cost - cached_cost
        savings_percentage = (savings / original_cost * 100) if original_cost > 0 else 0
        
        return {
            'original_cost': original_cost,
            'cached_cost': cached_cost,
            'savings': savings,
            'savings_percentage': savings_percentage
        }

