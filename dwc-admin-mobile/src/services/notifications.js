/**
 * Push Notification Service for DWC Admin Mobile App
 * Based on Expo Notifications best practices
 */

import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { registerPushToken } from './api';

// Configure notification handler
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,  // Replaces shouldShowAlert
    shouldShowList: true,
  }),
});

/**
 * Register for push notifications and get Expo Push Token
 * @returns {Promise<string|null>} Expo Push Token
 */
export async function registerForPushNotificationsAsync() {
  let token = null;

  // Android requires a notification channel
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('dwc-admin-messages', {
      name: 'Chat Messages',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#667eea',
      sound: 'default',
      enableVibrate: true,
    });
  }

  // Must use physical device for push notifications
  if (Device.isDevice) {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    // Request permission if not granted
    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== 'granted') {
      console.warn('Failed to get push notification permissions');
      return null;
    }

    try {
      // Get Expo project ID from app.json
      const projectId =
        Constants?.expoConfig?.extra?.eas?.projectId ??
        Constants?.easConfig?.projectId;

      if (!projectId) {
        console.warn('Project ID not found - using development mode');
        // For development without EAS, we can still get a token
        token = (await Notifications.getExpoPushTokenAsync()).data;
      } else {
        token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
      }

      console.log('Expo Push Token:', token);

      // Register token with backend
      try {
        await registerPushToken(token);
        console.log('Push token registered with backend');
      } catch (error) {
        console.error('Failed to register push token with backend:', error);
      }
    } catch (error) {
      console.error('Error getting push token:', error);
      token = null;
    }
  } else {
    console.warn('Must use physical device for Push Notifications');
  }

  return token;
}

/**
 * Setup notification listeners
 * @param {Function} onNotificationReceived - Called when notification is received while app is open
 * @param {Function} onNotificationTapped - Called when user taps a notification
 * @returns {Function} Cleanup function to remove listeners
 */
export function setupNotificationListeners(onNotificationReceived, onNotificationTapped) {
  // Listener for notifications received while app is in foreground
  const notificationListener = Notifications.addNotificationReceivedListener(notification => {
    console.log('Notification received:', notification);
    if (onNotificationReceived) {
      onNotificationReceived(notification);
    }
  });

  // Listener for when user taps on notification
  const responseListener = Notifications.addNotificationResponseReceivedListener(response => {
    console.log('Notification tapped:', response);
    if (onNotificationTapped) {
      onNotificationTapped(response);
    }
  });

  // Return cleanup function
  return () => {
    notificationListener.remove();
    responseListener.remove();
  };
}

/**
 * Schedule a local notification (for testing)
 * @param {string} title
 * @param {string} body
 * @param {object} data
 */
export async function scheduleLocalNotification(title, body, data = {}) {
  await Notifications.scheduleNotificationAsync({
    content: {
      title,
      body,
      data,
      sound: 'default',
    },
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL,
      seconds: 1,
    },
  });
}

/**
 * Show immediate local notification for new message
 * This works even when app is in background
 * @param {string} userId - The user ID of the sender
 * @param {string} message - The message text
 * @param {string} channel - The channel (webchat, sms, etc)
 */
export async function showNewMessageNotification(userId, message, channel = 'webchat') {
  await Notifications.scheduleNotificationAsync({
    content: {
      title: `New message from ${userId}`,
      body: message || 'New message received',
      data: {
        type: 'new_message',
        userId,
        channel,
        timestamp: new Date().toISOString(),
      },
      sound: 'default',
      priority: Notifications.AndroidNotificationPriority.HIGH,
      vibrate: [0, 250, 250, 250],
    },
    trigger: null, // Show immediately
  });
}

/**
 * Show notification for new conversation
 * @param {string} userId
 * @param {string} channel
 */
export async function showNewConversationNotification(userId, channel = 'webchat') {
  await Notifications.scheduleNotificationAsync({
    content: {
      title: '🆕 New Chat Started',
      body: `${userId} started a conversation on ${channel}`,
      data: {
        type: 'new_conversation',
        userId,
        channel,
        timestamp: new Date().toISOString(),
      },
      sound: 'default',
      priority: Notifications.AndroidNotificationPriority.HIGH,
      vibrate: [0, 250, 250, 250],
    },
    trigger: null, // Show immediately
  });
}
