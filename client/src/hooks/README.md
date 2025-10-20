# Custom Hooks

This directory contains custom React hooks for the Commission Tracker application.

## useThemeHydration

### Purpose
Prevents hydration mismatches in Next.js applications when using theme-dependent content. This hook ensures that theme-dependent rendering only occurs after the component has mounted on the client side.

### Problem Solved
Next.js hydration errors occur when the server-rendered HTML doesn't match the client-rendered HTML. This commonly happens with:
- Theme-dependent content (dark/light mode)
- Browser-specific APIs
- Local storage values
- User preferences

### Usage

```tsx
import { useThemeHydration } from '@/hooks/useThemeHydration';

function MyComponent() {
  const { mounted, isDark, isLight, isSystem } = useThemeHydration();

  // Don't render theme-dependent content until mounted
  if (!mounted) {
    return <LoadingScreen />;
  }

  return (
    <div className={isDark ? 'dark' : ''}>
      {/* Theme-dependent content */}
    </div>
  );
}
```

### API

| Property | Type | Description |
|----------|------|-------------|
| `mounted` | `boolean` | Whether the component has mounted on the client |
| `actualTheme` | `string` | The current theme value |
| `isDark` | `boolean` | True if theme is dark and component is mounted |
| `isLight` | `boolean` | True if theme is light and component is mounted |
| `isSystem` | `boolean` | True if theme is system and component is mounted |

### Implementation Details

The hook uses:
- `useState` to track mount status
- `useEffect` to set mounted to true after component mounts
- `useTheme` from the theme context to get current theme
- Computed properties for theme state checks

### Best Practices

1. **Always check `mounted` before rendering theme-dependent content**
2. **Provide a loading state while `mounted` is false**
3. **Use the computed properties (`isDark`, `isLight`) instead of direct theme checks**
4. **Keep the loading state consistent across your app**

### Example Implementation

```tsx
// ❌ Bad - causes hydration mismatch
function BadComponent() {
  const { actualTheme } = useTheme();
  
  return (
    <div className={actualTheme === 'dark' ? 'dark' : ''}>
      {/* This will cause hydration mismatch */}
    </div>
  );
}

// ✅ Good - prevents hydration mismatch
function GoodComponent() {
  const { mounted, isDark } = useThemeHydration();
  
  if (!mounted) {
    return <LoadingScreen />;
  }
  
  return (
    <div className={isDark ? 'dark' : ''}>
      {/* Safe to render theme-dependent content */}
    </div>
  );
}
```

### Related Components

- `LoadingScreen` - Reusable loading component
- `ThemeContext` - Theme context provider
- `ThemeProvider` - Theme provider component
