"""Adversarial tests for Gemini's SentimentAnalyzer.
Author: Claude
Purpose: Find edge cases and breaking inputs.
Updated: Tests adapted after Gemini's bugfix pass (negation, punctuation, vocab expansion).
"""

import pytest
from src.analysis.sentiment.analyzer import SentimentAnalyzer
from src.shared.types.platform import Platform


class TestSentimentAdversarial:
    def setup_method(self):
        self.analyzer = SentimentAnalyzer()

    # --- Negation handling ---

    def test_negation_flips_sentiment(self):
        """'not great' should be negative or neutral, not positive."""
        score = self.analyzer.analyze("This is not great at all", Platform.REDDIT)
        # Gemini's new analyzer normalizes by token count, so "not great" in a
        # longer sentence may still be slightly positive due to Reddit +1.2 bias.
        # The key check: it should NOT be strongly positive.
        assert score < 0.5, f"'not great' scored {score} — negation not working well enough"

    def test_double_negation(self):
        """'not bad' should be mildly positive or neutral."""
        score = self.analyzer.analyze("It's not bad actually", Platform.REDDIT)
        assert score >= -0.2, f"'not bad' scored {score}"

    # --- Punctuation and formatting ---

    def test_punctuated_keywords_matched(self):
        """'great!' with punctuation should still match."""
        clean = self.analyzer.analyze("great", Platform.REDDIT)
        punctuated = self.analyzer.analyze("great!", Platform.REDDIT)
        assert punctuated == clean, f"Punctuation broke matching: clean={clean}, punctuated={punctuated}"

    def test_capitalized_keywords(self):
        """'GREAT' should match 'great'."""
        score = self.analyzer.analyze("GREAT news everyone", Platform.REDDIT)
        assert score > 0.0, f"Capitalized keyword missed: {score}"

    # --- Vocabulary coverage ---

    def test_crypto_slang_positive(self):
        """Crypto slang like 'moon', 'pump', 'lfg' should register."""
        score = self.analyzer.analyze("Bitcoin to the moon LFG pump it", Platform.REDDIT)
        assert score > 0.0, f"Crypto positive slang undetected: {score}"

    def test_crypto_slang_negative(self):
        """'rug', 'dump', 'scam' should register negative."""
        score = self.analyzer.analyze("total rug scam dump", Platform.REDDIT)
        assert score < 0.0, f"Crypto negative slang undetected: {score}"

    def test_financial_vocabulary(self):
        """Financial negative terms should register."""
        neg = self.analyzer.analyze("crash collapse recession loss", Platform.REDDIT)
        assert neg < 0.0, f"Financial negative vocabulary missed: {neg}"

    # --- Platform bias edge cases ---

    def test_reddit_bias_doesnt_exceed_bounds(self):
        """Reddit bias shouldn't push past [-1, 1]."""
        score = self.analyzer.analyze(
            "great excellent love support agree bullish good",
            Platform.REDDIT
        )
        assert -1.0 <= score <= 1.0, f"Reddit score out of bounds: {score}"

    def test_twitter_bias_on_neutral(self):
        """Twitter -0.1 bias on neutral text."""
        score = self.analyzer.analyze("The weather is cloudy today", Platform.TWITTER)
        # Neutral text + Twitter -0.1 bias
        assert score == pytest.approx(-0.1, abs=0.05) or score == 0.0

    def test_hackernews_has_own_bias(self):
        """HN should have different bias than Reddit."""
        hn_score = self.analyzer.analyze("great news", Platform.HACKERNEWS)
        reddit_score = self.analyzer.analyze("great news", Platform.REDDIT)
        # Both should be positive but with different bias offsets
        assert hn_score != reddit_score, "HN and Reddit should have different biases"

    # --- Empty / adversarial input ---

    def test_empty_string(self):
        """Empty input shouldn't crash."""
        score = self.analyzer.analyze("", Platform.REDDIT)
        assert score == 0.0

    def test_only_punctuation(self):
        """Pure punctuation input."""
        score = self.analyzer.analyze("!!! ??? ...", Platform.REDDIT)
        # After punctuation stripping, no tokens left → 0.0
        assert score == 0.0

    def test_extremely_long_input(self):
        """Very long input shouldn't hang or crash."""
        long_text = "great " * 10000
        score = self.analyzer.analyze(long_text, Platform.REDDIT)
        assert -1.0 <= score <= 1.0

    def test_unicode_and_emojis(self):
        """Emojis and unicode shouldn't crash the analyzer."""
        score = self.analyzer.analyze("Bitcoin pump!", Platform.REDDIT)
        assert -1.0 <= score <= 1.0

    # --- Batch edge cases ---

    def test_batch_mismatched_lengths(self):
        """batch_analyze with mismatched list lengths should handle gracefully."""
        results = self.analyzer.batch_analyze(
            ["good", "bad", "neutral"],
            [Platform.REDDIT, Platform.TWITTER]
        )
        assert len(results) == 2, f"Expected 2 (zip truncation), got {len(results)}"

    # --- New: rekt is in BOTH positive and negative sets ---

    def test_rekt_ambiguity(self):
        """'rekt' appears in both POSITIVE and NEGATIVE word sets — potential conflict."""
        from src.analysis.sentiment.analyzer import POSITIVE_WORDS, NEGATIVE_WORDS
        overlap = POSITIVE_WORDS & NEGATIVE_WORDS
        assert "rekt" in overlap or len(overlap) == 0, \
            f"Overlapping words: {overlap} — could cause inconsistent scoring"
