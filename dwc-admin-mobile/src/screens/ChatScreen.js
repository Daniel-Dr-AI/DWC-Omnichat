/**
 * Chat Screen for DWC Admin Mobile App
 * Real-time messaging interface
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  FlatList,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { fetchMessages, sendMessage } from '../services/api';
import websocketService from '../services/websocket';

export default function ChatScreen({ route, navigation }) {
  const { conversation, isFollowup, isHistory } = route.params;
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false);
  const [visitorTyping, setVisitorTyping] = useState(false);
  const flatListRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  useEffect(() => {
    // Set navigation title
    navigation.setOptions({
      title: isFollowup
        ? conversation.name || conversation.user_id
        : conversation.user_id,
    });

    // Load messages if not a followup
    if (!isFollowup) {
      loadMessages();
    }

    // Listen for real-time messages via WebSocket
    const unsubscribe = websocketService.addListener(handleWebSocketMessage);

    return () => unsubscribe();
  }, []);

  const loadMessages = async () => {
    try {
      setLoading(true);
      console.log('Loading messages for:', conversation.user_id, conversation.channel);
      const data = await fetchMessages(conversation.user_id, conversation.channel);
      console.log('Messages loaded:', data.messages?.length || 0);
      setMessages(data.messages || []);
      scrollToBottom();
    } catch (error) {
      console.error('Error loading messages:', error);
      Alert.alert('Error', `Failed to load messages: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleWebSocketMessage = (data) => {
    // Check if message is for this conversation
    const isThisConversation =
      data.user_id === conversation.user_id &&
      data.channel === conversation.channel;

    if (!isThisConversation) return;

    // Handle typing indicators
    if (data.type === 'typing') {
      setVisitorTyping(true);
      // Clear existing timeout
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      // Auto-hide after 3 seconds
      typingTimeoutRef.current = setTimeout(() => {
        setVisitorTyping(false);
      }, 3000);
    } else if (data.type === 'stop_typing') {
      setVisitorTyping(false);
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    }
    // Handle regular messages
    else if (data.type === 'message' || !data.type) {
      setMessages((prev) => [...prev, data]);
      setVisitorTyping(false); // Hide typing when message arrives
      scrollToBottom();
    }
  };

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const messageText = inputText.trim();
    setInputText('');
    setSending(true);

    try {
      await sendMessage(conversation.user_id, conversation.channel, messageText);
      // Message will be added via WebSocket broadcast - no need for optimistic update
      scrollToBottom();
    } catch (error) {
      console.error('Error sending message:', error);
      Alert.alert('Error', 'Failed to send message');
      setInputText(messageText); // Restore text on error
    } finally {
      setSending(false);
    }
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 100);
  };

  // Send typing indicator when user types
  const handleTextChange = (text) => {
    setInputText(text);

    if (!isFollowup && text.trim()) {
      // Send typing event
      websocketService.send({
        type: 'staff_typing',
        user_id: conversation.user_id,
        channel: conversation.channel,
      });

      // Clear existing timeout
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }

      // Send stop_typing after 2 seconds of inactivity
      typingTimeoutRef.current = setTimeout(() => {
        websocketService.send({
          type: 'staff_stop_typing',
          user_id: conversation.user_id,
          channel: conversation.channel,
        });
      }, 2000);
    }
  };

  const renderMessage = ({ item }) => {
    const isStaff = item.sender === 'staff' || item.sender === 'admin';

    return (
      <View
        style={[
          styles.messageBubble,
          isStaff ? styles.staffMessage : styles.userMessage,
        ]}
      >
        <Text style={styles.senderText}>
          {isStaff ? 'You' : item.sender || 'User'}
        </Text>
        <Text style={styles.messageText}>{item.text}</Text>
        <Text style={styles.timestampText}>
          {new Date(item.ts).toLocaleTimeString()}
        </Text>
      </View>
    );
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      {/* Followup Info Banner */}
      {isFollowup && (
        <View style={styles.followupBanner}>
          <Text style={styles.followupTitle}>Followup Request</Text>
          {conversation.email && (
            <Text style={styles.followupInfo}>📧 {conversation.email}</Text>
          )}
          {conversation.phone && (
            <Text style={styles.followupInfo}>📱 {conversation.phone}</Text>
          )}
          {conversation.message && (
            <Text style={styles.followupMessage}>{conversation.message}</Text>
          )}
          <Text style={styles.followupNote}>
            This is a contact form submission. No active chat session.
          </Text>
        </View>
      )}

      {/* Messages List */}
      {!isFollowup ? (
        <>
          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#667eea" />
              <Text style={styles.loadingText}>Loading messages...</Text>
            </View>
          ) : (
            <FlatList
              ref={flatListRef}
              data={messages}
              renderItem={renderMessage}
              keyExtractor={(item, index) => `${item.ts}-${index}`}
              contentContainerStyle={styles.messagesContainer}
              ListEmptyComponent={
                <View style={styles.emptyContainer}>
                  <Text style={styles.emptyText}>No messages yet</Text>
                </View>
              }
            />
          )}
          {/* Typing Indicator */}
          {!loading && visitorTyping && (
            <View style={styles.typingIndicator}>
              <Text style={styles.typingText}>User is typing...</Text>
            </View>
          )}
        </>
      ) : (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>
            Contact the user via the provided email or phone
          </Text>
        </View>
      )}

      {/* Input Bar - Only show for active conversations (not history or followups) */}
      {!isFollowup && !isHistory && (
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder="Type a message..."
            value={inputText}
            onChangeText={handleTextChange}
            multiline
            maxLength={1000}
          />
          <TouchableOpacity
            style={[styles.sendButton, sending && styles.sendButtonDisabled]}
            onPress={handleSendMessage}
            disabled={sending || !inputText.trim()}
          >
            <Text style={styles.sendButtonText}>Send</Text>
          </TouchableOpacity>
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  followupBanner: {
    backgroundColor: '#fff3cd',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#ffc107',
  },
  followupTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#856404',
    marginBottom: 8,
  },
  followupInfo: {
    fontSize: 14,
    color: '#856404',
    marginBottom: 4,
  },
  followupMessage: {
    fontSize: 14,
    color: '#856404',
    marginTop: 8,
    fontStyle: 'italic',
  },
  followupNote: {
    fontSize: 12,
    color: '#999',
    marginTop: 8,
  },
  messagesContainer: {
    padding: 16,
  },
  messageBubble: {
    maxWidth: '80%',
    padding: 12,
    borderRadius: 16,
    marginBottom: 12,
  },
  staffMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#667eea',
  },
  userMessage: {
    alignSelf: 'flex-start',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  senderText: {
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 4,
    opacity: 0.7,
  },
  messageText: {
    fontSize: 16,
    color: '#333',
  },
  timestampText: {
    fontSize: 11,
    marginTop: 4,
    opacity: 0.6,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    textAlign: 'center',
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  input: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginRight: 8,
    maxHeight: 100,
    fontSize: 16,
  },
  sendButton: {
    backgroundColor: '#667eea',
    borderRadius: 20,
    paddingHorizontal: 20,
    justifyContent: 'center',
  },
  sendButtonDisabled: {
    opacity: 0.5,
  },
  sendButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  typingIndicator: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#f5f5f5',
  },
  typingText: {
    fontSize: 14,
    color: '#667eea',
    fontStyle: 'italic',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#667eea',
  },
});
