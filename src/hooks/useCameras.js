import { useCallback, useMemo } from 'react';
import { useApp } from '../context/AppContext';

export function useCameras() {
  const { cameras, loading, error } = useApp();

  const getCamera = useCallback(
    (id) => cameras.find((cam) => cam.id === id) ?? null,
    [cameras]
  );

  const filterCameras = useCallback(
    (filters = {}) => {
      const { status, location, search } = filters;
      const query = String(search || '').toLowerCase().trim();

      return cameras.filter((cam) => {
        if (status && cam.status !== status) return false;

        if (location) {
          const loc = String(location).toLowerCase().trim();
          const matchesLocation =
            cam.sector.toLowerCase().includes(loc) || cam.location.toLowerCase().includes(loc);
          if (!matchesLocation) return false;
        }

        if (query) {
          const haystack = `${cam.id} ${cam.name} ${cam.sector} ${cam.location} ${cam.status}`.toLowerCase();
          if (!haystack.includes(query)) return false;
        }

        return true;
      });
    },
    [cameras]
  );

  const summary = useMemo(() => {
    return cameras.reduce(
      (acc, cam) => {
        acc[cam.status] = (acc[cam.status] || 0) + 1;
        return acc;
      },
      { online: 0, warning: 0, offline: 0 }
    );
  }, [cameras]);

  return { cameras, loading, error, getCamera, filterCameras, summary };
}