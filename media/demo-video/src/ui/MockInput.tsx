import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { fontDisplay, fontMono } from "../shared/fonts";
import { theme } from "../shared/theme";

interface MockInputProps {
  text: string;
  typingStartFrame: number;
  charsPerSecond?: number;
  label?: string;
  mono?: boolean;
  placeholder?: string;
}

/**
 * Animated input with typing effect.
 * Characters reveal via string slicing, blinking cursor.
 */
export const MockInput: React.FC<MockInputProps> = ({
  text,
  typingStartFrame,
  charsPerSecond = 12,
  label,
  mono = false,
  placeholder = "",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const framesPerChar = Math.round(fps / charsPerSecond);
  const typingFrame = Math.max(0, frame - typingStartFrame);
  const revealedCount = Math.min(
    text.length,
    Math.floor(typingFrame / framesPerChar),
  );

  const displayedText = text.substring(0, revealedCount);
  const isTypingDone = revealedCount >= text.length;

  // Blinking cursor: toggle every 15 frames (~0.5s at 30fps)
  const cursorVisible = !isTypingDone || Math.floor(frame / 15) % 2 === 0;

  const showPlaceholder = revealedCount === 0 && frame < typingStartFrame;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {label && (
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: 13,
            fontWeight: 500,
            color: theme.textDark,
          }}
        >
          {label}
        </span>
      )}
      <div
        style={{
          background: "rgba(255,255,255,0.96)",
          border: `1px solid ${theme.borderStrong}`,
          borderRadius: 8,
          padding: "10px 14px",
          fontFamily: mono ? fontMono : fontDisplay,
          fontSize: 15,
          color: showPlaceholder ? theme.textMuted : theme.textDark,
          minWidth: 300,
          display: "flex",
          alignItems: "center",
          boxShadow: "0 1px 2px rgba(15, 23, 42, 0.03)",
        }}
      >
        <span>{showPlaceholder ? placeholder : displayedText}</span>
        {!showPlaceholder && cursorVisible && (
          <span
            style={{
              display: "inline-block",
              width: 2,
              height: 18,
              backgroundColor: theme.accent,
              marginLeft: 1,
            }}
          />
        )}
      </div>
    </div>
  );
};
