import { memo } from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { teaserTheme } from "../theme";
import { fontDisplay } from "../../shared/fonts";
import taxonData from "../data/taxon-vedette.json";

interface TaxonomicNavProps {
  startFrame?: number;
  /** Frames pour révéler tous les items. Default 18. */
  revealDurationFrames?: number;
  /** Largeur de la sidebar. Default 260. */
  width?: number;
}

interface TreeNode {
  level: string;
  name: string;
  active?: boolean;
  children?: TreeNode[];
}

/**
 * Sidebar taxonomique à gauche de la page taxon.
 * Référence visuelle : `/fr/taxons/948049381.html` zone gauche « Navigation taxonomique ».
 *
 * Header vert + liste hiérarchique arbres/caret/chevron + item sélectionné
 * (background vert clair + left border 3px vert).
 */
export const TaxonomicNav = memo<TaxonomicNavProps>(({ startFrame = 0, revealDurationFrames = 18, width = 260 }) => {
  const frame = useCurrentFrame();
  const localFrame = Math.max(0, frame - startFrame);

  // Flattened tree pour reveal stagger simple
  const flatItems = flattenTree(taxonData.taxonomicHierarchy);

  return (
    <div
      style={{
        width,
        background: teaserTheme.cardWhite,
        borderRadius: 12,
        overflow: "hidden",
        boxShadow: teaserTheme.shadowCard,
        display: "flex",
        flexDirection: "column",
        maxHeight: "100%",
      }}
    >
      {/* Header vert */}
      <div
        style={{
          background: teaserTheme.widgetHeaderGradient,
          padding: "12px 16px",
          color: teaserTheme.textOnPrimary,
          fontFamily: fontDisplay,
          fontSize: 14,
          fontWeight: 600,
        }}
      >
        Navigation taxonomique
      </div>

      {/* Search mock */}
      <div style={{ padding: "10px 12px" }}>
        <div
          style={{
            height: 30,
            borderRadius: 6,
            border: `1px solid ${teaserTheme.borderStrong}`,
            background: teaserTheme.pageBg,
            padding: "0 10px",
            display: "flex",
            alignItems: "center",
            fontFamily: fontDisplay,
            fontSize: 12,
            color: teaserTheme.textMuted,
          }}
        >
          Rechercher…
        </div>
      </div>

      {/* Tree items */}
      <div style={{ flex: 1, overflow: "hidden", padding: "0 4px 12px" }}>
        {flatItems.map((item, idx) => {
          const itemRevealFrame = (idx / flatItems.length) * revealDurationFrames;
          const opacity = interpolate(localFrame, [itemRevealFrame, itemRevealFrame + 4], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return <TreeItem key={`${item.level}-${item.name}-${idx}`} item={item} depth={item.depth} opacity={opacity} />;
        })}
      </div>
    </div>
  );
});

TaxonomicNav.displayName = "TaxonomicNav";

/* -------------------------- helpers -------------------------- */

type FlatItem = TreeNode & { depth: number; expanded: boolean };

function flattenTree(nodes: TreeNode[], depth = 0, out: FlatItem[] = []): FlatItem[] {
  for (const node of nodes) {
    const expanded = Boolean(node.active || node.children?.some(hasActiveDescendant));
    out.push({ ...node, depth, expanded });
    if (expanded && node.children) {
      flattenTree(node.children, depth + 1, out);
    }
  }
  return out;
}

function hasActiveDescendant(node: TreeNode): boolean {
  if (node.active) return true;
  return Boolean(node.children?.some(hasActiveDescendant));
}

const TreeItem: React.FC<{ item: FlatItem; depth: number; opacity: number }> = ({ item, depth, opacity }) => {
  const isActive = item.active;
  const indent = 8 + depth * 14;
  const hasChildren = Boolean(item.children && item.children.length > 0);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        padding: `6px 8px 6px ${indent}px`,
        borderRadius: 6,
        background: isActive ? teaserTheme.successBg : "transparent",
        borderLeft: isActive ? `3px solid ${teaserTheme.primary}` : "3px solid transparent",
        fontFamily: fontDisplay,
        fontSize: 12,
        fontWeight: isActive ? 600 : 400,
        color: isActive ? teaserTheme.primary : teaserTheme.textPrimary,
        opacity,
        transition: "none",
      }}
    >
      {hasChildren && (
        <span style={{ marginRight: 4, fontSize: 10, color: teaserTheme.textSecondary }}>{item.expanded ? "▾" : "▸"}</span>
      )}
      <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", fontStyle: item.level === "species" ? "italic" : "normal" }}>
        {item.name}
      </span>
    </div>
  );
};
