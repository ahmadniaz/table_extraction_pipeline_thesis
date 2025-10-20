/**
 * WebSocket Progress Integration Hook
 * 
 * Real-time progress tracking for upload and extraction process
 */

import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Get WebSocket base URL from API URL
 * Converts http://example.com or https://example.com to ws://example.com or wss://example.com
 */
function getWebSocketBaseUrl(): string {
  if (typeof window === 'undefined') {
    return 'ws://localhost:8000';
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  
  if (apiUrl) {
    // Extract the domain from the API URL and convert protocol
    const url = apiUrl.replace(/^https?:\/\//, '');
    const protocol = apiUrl.startsWith('https') ? 'wss:' : 'ws:';
    return `${protocol}//${url}`;
  }
  
  // Fallback for development
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname;
  return `${protocol}//${host}:8000`;
}

export interface ProgressState {
  currentStep: number;
  percentage: number;
  message: string;
  estimatedTimeRemaining: string | null;
  isConnected: boolean;
  error: string | null;
}

export interface ProgressMessage {
  type: 'STEP_STARTED' | 'STEP_PROGRESS' | 'STEP_COMPLETED' | 'EXTRACTION_COMPLETE' | 'ERROR' | 'ping' | 'pong' | 'connection_established';
  stepIndex?: number;
  stepId?: string;
  message?: string;
  percentage?: number;
  estimatedTime?: string;
  results?: any;
  error?: string;
  timestamp?: string | number;
  upload_id?: string;
  session_id?: string;
  connection_count?: number;
}

interface UseProgressWebSocketOptions {
  uploadId?: string;
  onExtractionComplete?: (results: any) => void;
  onError?: (error: string) => void;
  autoConnect?: boolean;
}

export function useProgressWebSocket({
  uploadId,
  onExtractionComplete,
  onError,
  autoConnect = true
}: UseProgressWebSocketOptions = {}) {
  const [progress, setProgress] = useState<ProgressState>({
    currentStep: 0,
    percentage: 0,
    message: '',
    estimatedTimeRemaining: null,
    isConnected: false,
    error: null
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const connectionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  
  // Enhanced timeout configuration for large file processing
  const CONNECTION_TIMEOUT = 60000; // 60 seconds to establish connection
  const HEARTBEAT_INTERVAL = 30000; // 30 seconds heartbeat
  
  // Store callbacks in refs to avoid recreating connect/disconnect on every render
  const onExtractionCompleteRef = useRef(onExtractionComplete);
  const onErrorRef = useRef(onError);
  const disconnectRef = useRef<(() => void) | null>(null);
  
  useEffect(() => {
    onExtractionCompleteRef.current = onExtractionComplete;
    onErrorRef.current = onError;
  }, [onExtractionComplete, onError]);

  const disconnect = useCallback(() => {
    // Clear all timers
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
    
    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
      connectionTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setProgress(prev => ({
      ...prev,
      isConnected: false
    }));
  }, []);
  
  // Store disconnect in ref
  useEffect(() => {
    disconnectRef.current = disconnect;
  }, [disconnect]);

  const connect = useCallback(() => {
    if (!uploadId) {
      console.log('⚠️ Cannot connect WebSocket: uploadId is missing');
      return;
    }

    // Close existing connection if any
    if (wsRef.current) {
      console.log('🔌 Closing existing WebSocket connection');
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      // Get auth token if available
      const token = localStorage.getItem('token');
      const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Get WebSocket base URL dynamically
      const wsBaseUrl = getWebSocketBaseUrl();
      
      // Build WebSocket URL with optional auth params
      let wsUrl = `${wsBaseUrl}/api/ws/progress/${uploadId}?session_id=${sessionId}`;
      if (token) {
        wsUrl += `&token=${token}`;
      }
      
      console.log('🔌 Connecting to WebSocket:', wsUrl.replace(/token=[^&]+/, 'token=***'));
      console.log('🔌 WebSocket Base URL:', wsBaseUrl);
      console.log('🔌 API URL:', process.env.NEXT_PUBLIC_API_URL);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      
      // Set connection timeout - close if not connected within timeout period
      connectionTimeoutRef.current = setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          console.error('❌ WebSocket connection timeout after 60 seconds');
          ws.close();
          setProgress(prev => ({
            ...prev,
            error: 'Connection timeout - please check your network',
            isConnected: false
          }));
          if (onErrorRef.current) {
            onErrorRef.current('WebSocket connection timeout');
          }
        }
      }, CONNECTION_TIMEOUT);

      ws.onopen = () => {
        console.log('✅ WebSocket connected successfully for uploadId:', uploadId);
        
        // Clear connection timeout
        if (connectionTimeoutRef.current) {
          clearTimeout(connectionTimeoutRef.current);
          connectionTimeoutRef.current = null;
        }
        
        setProgress(prev => ({
          ...prev,
          isConnected: true,
          error: null
        }));
        reconnectAttemptsRef.current = 0;
        
        // Send initial ping to confirm connection
        try {
          ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
        } catch (error) {
          console.error('Failed to send ping:', error);
        }
        
        // Start heartbeat interval to maintain connection during long-running processes
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            try {
              ws.send(JSON.stringify({ type: 'heartbeat', timestamp: Date.now() }));
              console.log('💓 Heartbeat sent to maintain connection');
            } catch (error) {
              console.error('Failed to send heartbeat:', error);
              if (heartbeatIntervalRef.current) {
                clearInterval(heartbeatIntervalRef.current);
                heartbeatIntervalRef.current = null;
              }
            }
          } else {
            console.warn('⚠️ WebSocket not open, clearing heartbeat interval');
            if (heartbeatIntervalRef.current) {
              clearInterval(heartbeatIntervalRef.current);
              heartbeatIntervalRef.current = null;
            }
          }
        }, HEARTBEAT_INTERVAL);
      };

      ws.onmessage = (event) => {
        try {
          const data: ProgressMessage = JSON.parse(event.data);
          
          // Handle server ping/pong
          if (data.type === 'ping') {
            // Respond to server ping with pong
            try {
              ws.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }));
              console.log('🏓 Responded to server ping with pong');
            } catch (error) {
              console.error('Failed to send pong:', error);
            }
            return;
          }
          
          if (data.type === 'pong') {
            // Server responded to our ping
            console.log('🏓 Received pong from server');
            return;
          }
          
          if (data.type === 'connection_established') {
            console.log('✅ WebSocket connection confirmed by server');
            return;
          }
          
          console.log('📨 WebSocket message:', data);
          handleProgressMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error for uploadId:', uploadId, error);
        console.error('WebSocket readyState:', ws.readyState);
        console.error('WebSocket URL was:', wsUrl.replace(/token=[^&]+/, 'token=***'));
        
        // Clear connection timeout on error
        if (connectionTimeoutRef.current) {
          clearTimeout(connectionTimeoutRef.current);
          connectionTimeoutRef.current = null;
        }
        
        setProgress(prev => ({
          ...prev,
          error: 'Connection error occurred',
          isConnected: false
        }));
        if (onErrorRef.current) {
          onErrorRef.current('WebSocket connection error');
        }
        
        // Implement exponential backoff retry
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          console.log(`🔄 Scheduling reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, delay);
        }
      };

      ws.onclose = (event) => {
        console.log('🔌 WebSocket disconnected for uploadId:', uploadId);
        console.log('Close code:', event.code, 'Reason:', event.reason || 'No reason provided');
        console.log('Was clean:', event.wasClean);
        
        // Clear heartbeat interval
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }
        
        // Clear connection timeout
        if (connectionTimeoutRef.current) {
          clearTimeout(connectionTimeoutRef.current);
          connectionTimeoutRef.current = null;
        }
        
        setProgress(prev => ({
          ...prev,
          isConnected: false
        }));

        // Attempt to reconnect if not a normal closure with exponential backoff
        if (event.code !== 1000 && event.code !== 1008 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          console.log(`🔄 Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, delay);
        } else {
          console.log('❌ Not reconnecting - code:', event.code, 'attempts:', reconnectAttemptsRef.current);
        }
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setProgress(prev => ({
        ...prev,
        error: 'Failed to establish connection',
        isConnected: false
      }));
    }
  }, [uploadId]);

  const handleProgressMessage = useCallback((data: ProgressMessage) => {
    switch (data.type) {
      case 'STEP_STARTED':
        setProgress(prev => ({
          ...prev,
          currentStep: data.stepIndex ?? prev.currentStep,
          message: data.message || '',
          percentage: data.percentage ?? prev.percentage,
          estimatedTimeRemaining: data.estimatedTime ?? prev.estimatedTimeRemaining
        }));
        break;

      case 'STEP_PROGRESS':
        setProgress(prev => ({
          ...prev,
          percentage: data.percentage ?? prev.percentage,
          estimatedTimeRemaining: data.estimatedTime ?? prev.estimatedTimeRemaining,
          message: data.message || prev.message
        }));
        break;

      case 'STEP_COMPLETED':
        setProgress(prev => ({
          ...prev,
          percentage: data.percentage ?? prev.percentage,
          message: data.message || `Step ${prev.currentStep + 1} completed`
        }));
        break;

      case 'EXTRACTION_COMPLETE':
        setProgress(prev => ({
          ...prev,
          currentStep: 4, // Final step (0-indexed, so step 5 = index 4)
          percentage: 100,
          message: 'Extraction complete!'
        }));
        if (onExtractionCompleteRef.current && data.results) {
          onExtractionCompleteRef.current(data.results);
        }
        // Close connection after completion
        setTimeout(() => {
          if (disconnectRef.current) {
            disconnectRef.current();
          }
        }, 1000);
        break;

      case 'ERROR':
        const errorMessage = data.error || 'An error occurred during processing';
        setProgress(prev => ({
          ...prev,
          error: errorMessage,
          isConnected: false
        }));
        if (onErrorRef.current) {
          onErrorRef.current(errorMessage);
        }
        break;

      default:
        console.warn('Unknown message type:', data.type);
    }
  }, []);

  const reset = useCallback(() => {
    disconnect();
    setProgress({
      currentStep: 0,
      percentage: 0,
      message: '',
      estimatedTimeRemaining: null,
      isConnected: false,
      error: null
    });
    reconnectAttemptsRef.current = 0;
  }, [disconnect]);

  // Auto-connect when uploadId is available
  useEffect(() => {
    if (autoConnect && uploadId) {
      connect();
    }

    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadId, autoConnect]);

  return {
    progress,
    connect,
    disconnect,
    reset,
    isConnected: progress.isConnected
  };
}

/**
 * Simplified hook for basic progress tracking without WebSocket
 */
export function useSimulatedProgress(duration: number = 20000) {
  const [progress, setProgress] = useState({
    currentStep: 0,
    percentage: 0,
    message: ''
  });

  const [isRunning, setIsRunning] = useState(false);

  const start = useCallback(() => {
    setIsRunning(true);
    const startTime = Date.now();
    const steps = 6;

    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const percentage = Math.min((elapsed / duration) * 100, 100);
      const currentStep = Math.min(Math.floor((elapsed / duration) * steps), steps - 1);

      setProgress({
        currentStep,
        percentage,
        message: `Processing step ${currentStep + 1} of ${steps}`
      });

      if (percentage >= 100) {
        clearInterval(interval);
        setIsRunning(false);
      }
    }, 100);

    return () => clearInterval(interval);
  }, [duration]);

  const reset = useCallback(() => {
    setProgress({
      currentStep: 0,
      percentage: 0,
      message: ''
    });
    setIsRunning(false);
  }, []);

  return {
    progress,
    isRunning,
    start,
    reset
  };
}

export default useProgressWebSocket;

