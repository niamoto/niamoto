import { useEffect } from 'react';
import { OverlayScrollbars } from 'overlayscrollbars';
import 'overlayscrollbars/overlayscrollbars.css';

/**
 * Initializes OverlayScrollbars on the body element.
 * This provides custom scrollbar styling that works across all platforms including Tauri/macOS.
 */
export function ScrollbarProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Initialize on body for global scrollbar styling
    const osInstance = OverlayScrollbars(document.body, {
      scrollbars: {
        theme: 'os-theme-custom',
        autoHide: 'leave',
        autoHideDelay: 400,
        clickScroll: true,
      },
      overflow: {
        x: 'hidden',
      },
    });

    return () => {
      osInstance.destroy();
    };
  }, []);

  return <>{children}</>;
}
