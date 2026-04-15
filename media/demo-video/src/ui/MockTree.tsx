import { useCurrentFrame, interpolate } from "remotion";
import { fontDisplay } from "../shared/fonts";
import { theme } from "../shared/theme";

export interface TreeItem {
  label: string;
  icon: string;
  type: "page" | "collection" | "template";
  children?: TreeItem[];
}

interface MockTreeProps {
  items: TreeItem[];
  activeItem?: string;
  expandAtFrame?: number;
}

const typeIcons: Record<string, React.FC<{ color: string; size?: number }>> = {
  page: ({ color, size = 14 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  ),
  collection: ({ color, size = 14 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8">
      <path d="M12 2 2 7l10 5 10-5-10-5z" />
      <path d="m2 17 10 5 10-5" />
      <path d="m2 12 10 5 10-5" />
    </svg>
  ),
  template: ({ color, size = 14 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M3 9h18" />
      <path d="M9 21V9" />
    </svg>
  ),
};

/**
 * Tree navigation for site builder.
 * Items expand progressively.
 */
export const MockTree: React.FC<MockTreeProps> = ({
  items,
  activeItem,
  expandAtFrame = 0,
}) => {
  const frame = useCurrentFrame();

  let itemIndex = 0;

  const renderItem = (item: TreeItem, depth: number): React.ReactNode => {
    const idx = itemIndex++;
    const isActive = item.label === activeItem;
    const IconComponent = typeIcons[item.type] || typeIcons.page;

    // Stagger entrance: each item appears 4 frames after the previous
    const enterFrame = expandAtFrame + idx * 4;
    const opacity = interpolate(frame, [enterFrame, enterFrame + 10], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

    const hasChildren = item.children && item.children.length > 0;

    return (
      <div key={item.label} style={{ opacity }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "5px 8px",
            paddingLeft: 8 + depth * 18,
            borderRadius: 4,
            background: isActive ? "rgba(75, 175, 80, 0.1)" : "transparent",
            cursor: "pointer",
          }}
        >
          {/* Expand indicator for collections */}
          {hasChildren ? (
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke={theme.textMuted} strokeWidth="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          ) : (
            <div style={{ width: 10 }} />
          )}

          <IconComponent color={isActive ? theme.lightGreen : theme.textMuted} />
          <span
            style={{
              fontFamily: fontDisplay,
              fontSize: 13,
              color: isActive ? theme.lightGreen : theme.textWhite,
              fontWeight: isActive ? 600 : 400,
            }}
          >
            {item.label}
          </span>
        </div>

        {/* Children */}
        {hasChildren &&
          item.children!.map((child) => renderItem(child, depth + 1))}
      </div>
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1, padding: "8px 4px" }}>
      {items.map((item) => renderItem(item, 0))}
    </div>
  );
};
