import React, { useEffect } from 'react';
import useStore from '../../store/useStore';
import './NotificationStack.css';

export default function NotificationStack() {
  const { notifications, removeNotification } = useStore();

  return (
    <div className="notif-stack" aria-live="polite" aria-label="Notifications">
      {notifications.map(n => (
        <Notification key={n.id} notif={n} onDismiss={removeNotification} />
      ))}
    </div>
  );
}

function Notification({ notif, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(() => onDismiss(notif.id), 4000);
    return () => clearTimeout(t);
  }, [notif.id, onDismiss]);

  return (
    <div className={`notif notif--${notif.type}`} role="alert">
      <span className="notif-msg">{notif.msg}</span>
      <button
        className="btn-icon"
        onClick={() => onDismiss(notif.id)}
        aria-label="Dismiss notification"
      >
        ✕
      </button>
    </div>
  );
}
