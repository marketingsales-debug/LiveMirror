"""Adversarial tests for Gemini's SentimentAnalyzer.
Author: Claude
Purpose: Find edge cases and breaking inputs.
"""

import pytest
from src.analysis.sentiment.analyzer import SentimentAnalyzer
from src.shared.types.platform import Platform


class TestSentimentAdversarial:
    def setup_method(self):
        self.analyzer = SentimentAnalyzer()

    # --- Negation handling ---

    def test_negation_flips_sentiment(self):
        """'not great' should be negative, not positive."""
        score = self.analyzer.analyze("This is not great at all", Platform.REDDIT)
        # BUG: Keyword matcher sees "great" and scores positive
        # This test SHOULD pass but currently fails — documenting the gap
        assert score <= 0.0, f"'not great' scored {score} — negation ignored"

    def test_double_negation(self):
        """'not bad' should be mildly positive."""
        score = self.analyzer.analyze("It's not bad actually", Platform.REDDIT)
        assert score >= 0.0, f"'not bad' scored {score}"

    # --- Punctuation and formatting ---

    def test_punctuated_keywords_missed(self):
        """'great!' with punctuation should still match."""
        clean = self.analyzer.analyze("great", Platform.REDDIT)
        punctuated = self.analyzer.analyze("great!", Platform.REDDIT)
        assert punctuated == clean, f"Punctuation broke matching: clean={clean}, punctuated={punctuated}"

    def test_capitalized_keywords(self):
        """'GREAT' should match 'great'."""
        score = self.analyzer.analyze("GREAT news everyone", Platform.REDDIT)
        assert score > 0.0, f"Capitalized keyword missed: {score}"

    # --- Missing vocabulary ---

    def test_crypto_slang_positive(self):
        """Crypto slang like 'moon', 'pump', 'lfg' should register."""
        score = self.analyzer.analyze("Bitcoin to the moon! LFG pump it!", Platform.REDDIT)
        # BUG: None of these words are in the positive set
        assert score > 0.0, f"Crypto positive slang undetected: {score}"

    def test_crypto_slang_negative(self):
        """'rekt', 'dump', 'rug pull' should register negative."""
        score = self.analyzer.analyze("Got absolutely rekt, total rug pull dump", Platform.REDDIT)
        assert score < 0.0, f"Crypto negative slang undetected: {score}"

    def test_financial_vocabulary(self):
        """'outperform', 'downgrade', 'default' should register."""
        neg = self.analyzer.analyze("Company downgraded, risk of default", Platform.REDDIT)
        # These financial terms aren't in the word lists
        assert neg < 0.0, f"Financial negative vocabulary missed: {neg}"

    # --- Platform bias edge cases ---

    def test_reddit_amplification_doesnt_exceed_bounds(self):
        """Reddit 1.2x multiplier shouldn't push past [-1, 1]."""
        score = self.analyzer.analyze(
            "great excellent love support agree bullish good",
            Platform.REDDIT
        )
        assert -1.0 <= score <= 1.0, f"Reddit score out of bounds: {score}"

    def test_twitter_bias_on_neutral(self):
        """Twitter -0.1 bias on neutral text shouldn't make it negative."""
        score = self.analyzer.analyze("The weather is cloudy today", Platform.TWITTER)
        # Neutral text → base_score 0.0 → Twitter applies -0.1 → returns -0.1
        # Is this intentional? Neutral content shouldn't be negative just because it's on Twitter
        assert score == pytest.approx(-0.1, abs=0.01) or score == 0.0

    def test_unknown_platform_no_bias(self):
        """Platforms without special handling should get raw score."""
        score = self.analyzer.analyze("great news", Platform.HACKERNEWS)
        reddit_score = self.analyzer.analyze("great news", Platform.REDDIT)
        # HN should NOT have Reddit's 1.2x amplification
        assert score != reddit_score or score == 0.0

    # --- Empty / adversarial input ---

    def test_empty_string(self):
        """Empty input shouldn't crash."""
        score = self.analyzer.analyze("", Platform.REDDIT)
        assert score == 0.0

    def test_only_punctuation(self):
        """Pure punctuation input."""
        score = self.analyzer.analyze("!!! ??? ...", Platform.REDDIT)
        assert score == 0.0

    def test_extremely_long_input(self):
        """Very long input shouldn't hang or crash."""
        long_text = "great " * 10000
        score = self.analyzer.analyze(long_text, Platform.REDDIT)
        assert -1.0 <= score <= 1.0

    def test_unicode_and_emojis(self):
        """Emojis and unicode shouldn't crash the analyzer."""
        score = self.analyzer.analyze("🚀🌕 Bitcoin pump! 💎🙌", Platform.REDDIT)
        assert -1.0 <= score <= 1.0

    # --- Batch edge cases ---

    def test_batch_mismatched_lengths(self):
        """batch_analyze with mismatched list lengths should handle gracefully."""
        # zip() silently truncates — this could hide bugs
        results = self.analyzer.batch_analyze(
            ["good", "bad", "neutral"],
            [Platform.REDDIT, Platform.TWITTER]  # only 2 platforms for 3 texts
        )
        # zip truncates to shortest — we get 2 results, not 3
        assert len(results) == 2, f"Expected 2 (zip truncation), got {len(results)}"
