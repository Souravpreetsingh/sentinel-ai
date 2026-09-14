import { useCallback, useMemo } from 'react';
import { useApp } from '../context/AppContext';

export function useIncidents() {
  const { incidents, loading, error } = useApp();

  const getIncident = useCallback(
    (id) => incidents.find((inc) => inc.id === id) ?? null,
    [incidents]
  );

  const filterIncidents = useCallback(
    (filters = {}) => {
      const { severity, status, search } = filters;
      const query = String(search || '').toLowerCase().trim();

      return incidents.filter((inc) => {
        if (severity && inc.severity !== severity) return false;
        if (status && inc.status !== status) return false;

        if (query) {
          const haystack =
            `${inc.id} ${inc.type} ${inc.location} ${inc.status} ${inc.severity} ${inc.description || ''}`.toLowerCase();
          if (!haystack.includes(query)) return false;
        }

        return true;
      });
    },
    [incidents]
  );

  const counts = useMemo(() => {
    return {
      totalCount: incidents.length,
      criticalCount: incidents.filter((inc) => inc.severity === 'critical').length,
      highCount: incidents.filter((inc) => inc.severity === 'high').length,
      mediumCount: incidents.filter((inc) => inc.severity === 'medium').length,
      lowCount: incidents.filter((inc) => inc.severity === 'low').length,
    };
  }, [incidents]);

  return { incidents, loading, error, getIncident, filterIncidents, ...counts };
}