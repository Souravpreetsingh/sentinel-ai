import { useEffect, useRef, useState } from 'react';

export function useFullscreen() {
  const ref = useRef(null);
  const [fsNative, setFsNative] = useState(false);
  const [fsWin, setFsWin] = useState(false);
  const isFullscreen = fsNative || fsWin;

  useEffect(() => {
    const onFsChange = () =>
      setFsNative(!!ref.current && document.fullscreenElement === ref.current);
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, []);

  useEffect(() => {
    if (!fsWin) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape' || e.key === 'Esc') setFsWin(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [fsWin]);

  const enterFullscreen = () => {
    const el = ref.current;
    if (!el) return;
    const nativeAvailable =
      typeof document !== 'undefined' &&
      document.fullscreenEnabled &&
      typeof el.requestFullscreen === 'function';
    if (nativeAvailable) {
      el.requestFullscreen().catch((err) => {
        console.warn('[sentinel] native fullscreen unavailable, using fallback:', err?.message || err);
        setFsWin(true);
      });
    } else {
      setFsWin(true);
    }
  };

  const exitFullscreen = () => {
    if (fsWin) {
      setFsWin(false);
      return;
    }
    if (typeof document !== 'undefined' && document.fullscreenElement) {
      document.exitFullscreen().catch((err) => {
        console.warn('[sentinel] exitFullscreen failed:', err?.message || err);
      });
    }
  };

  const toggleFullscreen = () => {
    if (isFullscreen) exitFullscreen();
    else enterFullscreen();
  };

  return { ref, isFullscreen, enterFullscreen, exitFullscreen, toggleFullscreen };
}