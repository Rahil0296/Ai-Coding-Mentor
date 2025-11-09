"""
Daily Learning Tips
Provides coding wisdom and best practices to inspire learners.
"""

import random
from datetime import datetime


class LearningTipsProvider:
    """Provides daily coding tips and best practices."""
    
    TIPS = [
        "💡 Write code for humans first, computers second. Clear variable names save hours of debugging.",
        "🚀 The best code is no code. Before adding features, ask: 'Do I really need this?'",
        "🔍 Debug by understanding, not guessing. Print statements are your best friend.",
        "📚 Read others' code daily. You'll learn patterns you'd never discover alone.",
        "⚡ Premature optimization is the root of all evil. Make it work, then make it fast.",
        "🎯 One function, one purpose. If you can't name it clearly, it's doing too much.",
        "🧪 Write tests. Future you will thank present you when refactoring.",
        "💬 Code comments explain WHY, not WHAT. The code itself shows what it does.",
        "🔄 Git commit often. Small commits = easy rollbacks and clear history.",
        "🎨 Consistency beats perfection. Pick a style and stick with it.",
        "🐛 Every bug teaches something. Keep a 'lessons learned' doc.",
        "🏃 Start simple, iterate fast. MVP → feedback → improve.",
        "📖 Documentation is love letter to your future self.",
        "🔐 Never trust user input. Validate, sanitize, escape—always.",
        "⏱️ Time complexity matters. O(n²) looks innocent until n=10,000.",
        "🎭 Functions should do one thing well, not many things poorly.",
        "🗑️ Delete code aggressively. Dead code is technical debt.",
        "🤝 Pair programming: Two heads debug faster than one.",
        "📊 Measure before optimizing. Intuition lies, profilers don't.",
        "🌱 Learn in public. Share your journey, help others, grow together.",
        "🚀 You miss 100% of the shots you don't take."
    ]
    
    @staticmethod
    def get_daily_tip() -> dict:
        """
        Get the daily learning tip.
        
        Uses date-based seeding so same tip appears all day,
        but changes daily.
        
        Returns:
            Dictionary with tip text and metadata
        """
        # Seed random with today's date for consistency
        today = datetime.utcnow().date()
        seed = int(today.strftime("%Y%m%d"))
        random.seed(seed)
        
        tip = random.choice(LearningTipsProvider.TIPS)
        
        return {
            "tip": tip,
            "date": today.isoformat(),
            "tip_number": (seed % len(LearningTipsProvider.TIPS)) + 1,
            "total_tips": len(LearningTipsProvider.TIPS)
        }
    
    @staticmethod
    def get_random_tip() -> str:
        """Get a random tip (not date-based)."""
        return random.choice(LearningTipsProvider.TIPS)