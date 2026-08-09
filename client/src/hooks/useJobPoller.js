import { useState, useEffect, useRef } from 'react';

export function useJobPoller(apiUrl) {
  const [isPolling, setIsPolling] = useState(false);
  const [status, setStatus] = useState('');
  const [progress, setProgress] = useState(0);
  const intervalRef = useRef(null);

  const clearPoller = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  useEffect(() => {
    return () => clearPoller(); // Cleanup on unmount
  }, []);

  const startPolling = (jobId, { onSuccess, onError }) => {
    setIsPolling(true);
    setStatus('Started processing...');
    setProgress(5);
    clearPoller();

    intervalRef.current = setInterval(async () => {
      try {
        const jobRes = await fetch(`${apiUrl}/jobs/${jobId}`);
        if (!jobRes.ok) throw new Error('Failed to retrieve job status');
        
        const jobData = await jobRes.json();
        setStatus(jobData.status || '');
        setProgress(jobData.progress || 0);
        
        if (jobData.status === 'completed') {
          clearPoller();
          setProgress(100);
          setTimeout(() => {
            setIsPolling(false);
            if (onSuccess) onSuccess(jobData.result);
          }, 500);
        } else if (jobData.status === 'failed') {
          clearPoller();
          setIsPolling(false);
          if (onError) onError(new Error(jobData.error || 'Unknown pipeline failure'));
        }
      } catch (err) {
        clearPoller();
        setIsPolling(false);
        if (onError) onError(err);
      }
    }, 1000);
  };

  return { isPolling, status, progress, startPolling, clearPoller };
}

export default useJobPoller;
