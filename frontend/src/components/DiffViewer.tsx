import React from "react";
import ReactDiffViewer, { DiffMethod } from "react-diff-viewer-continued";

interface DiffViewerProps {
  originalCode: string;
  refactoredCode: string;
  language?: string;
  fileName?: string;
}

export default function DiffViewer({ originalCode, refactoredCode, language = "javascript", fileName }: DiffViewerProps) {
  const newStyles = {
    variables: {
      dark: {
        diffViewerBackground: "#030712",
        diffViewerColor: "#f9fafb",
        addedBackground: "#064e3b20",
        addedColor: "#10b981",
        removedBackground: "#7f1d1d20",
        removedColor: "#ef4444",
        wordAddedBackground: "#06573120",
        wordRemovedBackground: "#99181820",
        addedGutterBackground: "#064e3b10",
        removedGutterBackground: "#7f1d1d10",
        gutterBackground: "#111827",
        gutterBackgroundDark: "#0f172a",
        highlightBackground: "#1f293730",
        highlightGutterBackground: "#1f293750",
        codeFoldGutterBackground: "#1f2937",
        codeFoldBackground: "#111827",
        emptyLineBackground: "#03071210",
        gutterColor: "#9ca3af",
        addedGutterColor: "#10b981",
        removedGutterColor: "#ef4444",
        codeFoldContentColor: "#6b7280",
        diffViewerTitleBackground: "#111827",
        diffViewerTitleColor: "#f9fafb",
        diffViewerTitleBorderColor: "#374151",
      },
      light: {
        diffViewerBackground: "#ffffff",
        diffViewerColor: "#111827",
        addedBackground: "#dcfce720",
        addedColor: "#16a34a",
        removedBackground: "#fee2e220",
        removedColor: "#dc2626",
        wordAddedBackground: "#dcfce740",
        wordRemovedBackground: "#fee2e240",
        addedGutterBackground: "#dcfce710",
        removedGutterBackground: "#fee2e210",
        gutterBackground: "#f9fafb",
        gutterBackgroundDark: "#f3f4f6",
        highlightBackground: "#e5e7eb30",
        highlightGutterBackground: "#e5e7eb50",
        codeFoldGutterBackground: "#f3f4f6",
        codeFoldBackground: "#f9fafb",
        emptyLineBackground: "#fafafa10",
        gutterColor: "#6b7280",
        addedGutterColor: "#16a34a",
        removedGutterColor: "#dc2626",
        codeFoldContentColor: "#9ca3af",
        diffViewerTitleBackground: "#f9fafb",
        diffViewerTitleColor: "#111827",
        diffViewerTitleBorderColor: "#e5e7eb",
      },
    },
    line: {
      padding: "6px 2px",
      fontSize: "12px",
      fontFamily: "'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace",
      lineHeight: "1.6",
    },
    gutter: {
      padding: "6px 8px",
      minWidth: "50px",
      textAlign: "right" as const,
      fontSize: "12px",
    },
    marker: {
      padding: "6px 10px",
    },
    contentText: {
      fontSize: "12px",
      fontFamily: "'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace",
      lineHeight: "1.6",
    },
    titleBlock: {
      padding: "8px 12px",
      fontSize: "13px",
      fontWeight: "500" as const,
    },
  };

  // Detect dark mode
  const isDarkMode = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  const useDarkTheme = isDarkMode;

  return (
    <div className="border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden">
      <ReactDiffViewer
        oldValue={originalCode}
        newValue={refactoredCode}
        splitView={true}
        compareMethod={DiffMethod.WORDS}
        useDarkTheme={useDarkTheme}
        styles={newStyles}
        leftTitle={fileName ? `Original: ${fileName}` : "Original Code"}
        rightTitle={fileName ? `Refactored: ${fileName}` : "Refactored Code"}
        hideLineNumbers={false}
        showDiffOnly={false}
        extraLinesSurroundingDiff={3}
      />
    </div>
  );
}
