/**
 * DWC Admin Mobile App
 * Main application component with navigation and authentication
 */

import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { StatusBar } from 'expo-status-bar';
import { TouchableOpacity, Text, StyleSheet } from 'react-native';

// Contexts
import { AuthProvider, useAuth } from './src/contexts/AuthContext';

// Screens
import LoginScreen from './src/screens/LoginScreen';
import ConversationsScreen from './src/screens/ConversationsScreen';
import ChatScreen from './src/screens/ChatScreen';

// Services
import {
  setupNotificationListeners,
  registerForPushNotificationsAsync,
  showNewMessageNotification,
  showNewConversationNotification
} from './src/services/notifications';
import websocketService from './src/services/websocket';
import { AppState } from 'react-native';

const Stack = createStackNavigator();

function AppNavigator() {
  const { isAuthenticated, logout } = useAuth();
  const appState = React.useRef(AppState.currentState);
  const [isAppInBackground, setIsAppInBackground] = React.useState(false);
  const isAppInBackgroundRef = React.useRef(false); // Add ref to avoid stale closure

  // Connect WebSocket when authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      websocketService.disconnect();
      return;
    }

    // Connect WebSocket
    websocketService.connect();

    // Register for push notifications
    registerForPushNotificationsAsync().catch(err => {
      console.error('Failed to register for push notifications:', err);
    });

    return () => {
      websocketService.disconnect();
    };
  }, [isAuthenticated]);

  // Monitor app state (foreground/background)
  useEffect(() => {
    const subscription = AppState.addEventListener('change', nextAppState => {
      const isGoingToBackground =
        appState.current.match(/active/) && nextAppState.match(/inactive|background/);
      const isComingToForeground =
        appState.current.match(/inactive|background/) && nextAppState === 'active';

      if (isGoingToBackground) {
        console.log('📱 App has gone to the background');
        setIsAppInBackground(true);
        isAppInBackgroundRef.current = true; // Update ref
      } else if (isComingToForeground) {
        console.log('📱 App has come to the foreground');
        setIsAppInBackground(false);
        isAppInBackgroundRef.current = false; // Update ref
      }

      console.log('📱 AppState changed:', {
        from: appState.current,
        to: nextAppState,
        isBackground: isGoingToBackground,
        isForeground: isComingToForeground
      });

      appState.current = nextAppState;
    });

    return () => {
      subscription.remove();
    };
  }, []);

  // Setup WebSocket message listener for notifications
  useEffect(() => {
    if (!isAuthenticated) return;

    const unsubscribe = websocketService.addListener((data) => {
      console.log('🔔 Notification listener received:', {
        type: data.type,
        sender: data.sender,
        isBackground: isAppInBackgroundRef.current, // Use ref for current value
        hasText: !!data.text
      });

      if (!isAppInBackgroundRef.current) { // Use ref instead of state
        console.log('⏭️  Skipping notification - app is in foreground');
        return; // Only notify when app is in background
      }

      // Handle regular incoming messages (type is empty or not set)
      if (data.sender === 'user' && data.user_id && data.text) {
        // Direct user message - show notification
        console.log('🔔 Showing notification for user message:', data.user_id, data.text);
        showNewMessageNotification(
          data.user_id,
          data.text,
          data.channel || 'webchat'
        ).catch(err => console.error('Failed to show notification:', err));
      }
      // Handle snapshot/update messages (for new conversations)
      else if (data.type === 'snapshot' || data.type === 'update') {
        if (data.data) {
          const { user_id, channel, messages } = data.data;
          const lastMessage = messages && messages.length > 0
            ? messages[messages.length - 1]
            : null;

          if (lastMessage && lastMessage.sender === 'user') {
            // Show notification for new user message in snapshot
            showNewMessageNotification(
              user_id,
              lastMessage.text,
              channel
            ).catch(err => console.error('Failed to show notification:', err));
          } else if (data.type === 'snapshot') {
            // New conversation started
            showNewConversationNotification(user_id, channel)
              .catch(err => console.error('Failed to show notification:', err));
          }
        }
      }
    });

    return unsubscribe;
  }, [isAuthenticated]); // Remove isAppInBackground from deps - we use ref now

  // Setup notification listeners
  useEffect(() => {
    if (!isAuthenticated) return;

    const cleanup = setupNotificationListeners(
      (notification) => {
        // Handle notification received while app is open
        console.log('Notification received:', notification);
      },
      (response) => {
        // Handle notification tapped
        console.log('Notification tapped:', response);
        // Could navigate to specific conversation here
      }
    );

    return cleanup;
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Login" component={LoginScreen} />
      </Stack.Navigator>
    );
  }

  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: '#667eea',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: '600',
        },
      }}
    >
      <Stack.Screen
        name="Conversations"
        component={ConversationsScreen}
        options={() => ({
          title: 'DWC Admin',
          headerRight: () => (
            <TouchableOpacity style={styles.logoutButton} onPress={logout}>
              <Text style={styles.logoutText}>Logout</Text>
            </TouchableOpacity>
          ),
        })}
      />
      <Stack.Screen
        name="Chat"
        component={ChatScreen}
        options={{
          title: 'Chat',
        }}
      />
    </Stack.Navigator>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <NavigationContainer>
        <StatusBar style="light" />
        <AppNavigator />
      </NavigationContainer>
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  logoutButton: {
    marginRight: 16,
    paddingVertical: 6,
    paddingHorizontal: 12,
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 6,
  },
  logoutText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
});
