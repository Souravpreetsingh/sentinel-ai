import { useCallback } from 'react';
import { useApp } from '../context/AppContext';

export function useAlerts() {
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    clearNotifications,
    addNotification,
  } = useApp();

  const markAll = useCallback(() => markAllAsRead(), [markAllAsRead]);
  const clearAll = useCallback(() => clearNotifications(), [clearNotifications]);

  return {
    notifications,
    unreadCount,
    markAsRead,
    markAll,
    clearAll,
    addNotification,
  };
}