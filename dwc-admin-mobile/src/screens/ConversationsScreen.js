/**
 * Conversations List Screen for DWC Admin Mobile App
 * Displays open, history, and followup conversations with tabs
 */

import { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { fetchOpenConversations, fetchHistory, fetchFollowups } from '../services/api';
import websocketService from '../services/websocket';

export default function ConversationsScreen({ navigation }) {
  const [activeTab, setActiveTab] = useState('open');
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadConversations();

    // Listen for WebSocket updates
    const unsubscribe = websocketService.addListener(handleWebSocketMessage);

    return () => unsubscribe();
  }, [activeTab]);

  const handleWebSocketMessage = (data) => {
    // Reload conversations when there's an update
    if (data.type === 'snapshot' || data.type === 'update') {
      loadConversations();
    }
  };

  const loadConversations = async () => {
    try {
      setLoading(true);
      let data;

      switch (activeTab) {
        case 'open':
          data = await fetchOpenConversations();
          setConversations(data.conversations || []);
          break;
        case 'history':
          data = await fetchHistory();
          setConversations(data.history || []);
          break;
        case 'followups':
          data = await fetchFollowups();
          setConversations(data.followups || []);
          break;
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadConversations();
  }, [activeTab]);

  const renderConversationItem = ({ item }) => {
    const isFollowup = activeTab === 'followups';
    const isHistory = activeTab === 'history';

    return (
      <TouchableOpacity
        style={styles.conversationItem}
        onPress={() => navigation.navigate('Chat', { conversation: item, isFollowup, isHistory })}
      >
        <View style={styles.conversationHeader}>
          <Text style={styles.userName}>
            {isFollowup ? item.name || item.user_id : item.user_id}
          </Text>
          <Text style={styles.channel}>{item.channel}</Text>
        </View>

        {isFollowup ? (
          <View style={styles.followupDetails}>
            {item.email && <Text style={styles.contactInfo}>📧 {item.email}</Text>}
            {item.phone && <Text style={styles.contactInfo}>📱 {item.phone}</Text>}
            {item.message && (
              <Text style={styles.messagePreview} numberOfLines={2}>
                {item.message}
              </Text>
            )}
          </View>
        ) : (
          <View style={styles.conversationDetails}>
            <Text style={styles.assigned}>
              {isHistory
                ? `Status: ${item.source === 'conversation' ? 'Closed' : 'Followup Archived'}`
                : `Assigned: ${item.assigned_staff || 'Unassigned'}`
              }
            </Text>
            <Text style={styles.messageCount}>
              {Array.isArray(item.messages)
                ? item.messages.length
                : item.message_count || 0}{' '}
              messages
            </Text>
          </View>
        )}

        <Text style={styles.timestamp}>
          {item.last_updated || item.updated_at || item.created_at || item.ts || 'N/A'}
        </Text>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      {/* Tab Bar */}
      <View style={styles.tabBar}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'open' && styles.activeTab]}
          onPress={() => setActiveTab('open')}
        >
          <Text style={[styles.tabText, activeTab === 'open' && styles.activeTabText]}>
            Open
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tab, activeTab === 'history' && styles.activeTab]}
          onPress={() => setActiveTab('history')}
        >
          <Text style={[styles.tabText, activeTab === 'history' && styles.activeTabText]}>
            History
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tab, activeTab === 'followups' && styles.activeTab]}
          onPress={() => setActiveTab('followups')}
        >
          <Text style={[styles.tabText, activeTab === 'followups' && styles.activeTabText]}>
            Followups
          </Text>
        </TouchableOpacity>
      </View>

      {/* Conversations List */}
      {loading && !refreshing ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#667eea" />
        </View>
      ) : (
        <FlatList
          data={conversations}
          renderItem={renderConversationItem}
          keyExtractor={(item, index) =>
            activeTab === 'followups'
              ? String(item.id || index)
              : `${item.user_id}-${item.channel}-${index}`
          }
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>No {activeTab} conversations</Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  tab: {
    flex: 1,
    paddingVertical: 16,
    alignItems: 'center',
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: '#667eea',
  },
  tabText: {
    fontSize: 16,
    color: '#666',
    fontWeight: '500',
  },
  activeTabText: {
    color: '#667eea',
    fontWeight: '600',
  },
  conversationItem: {
    backgroundColor: '#fff',
    padding: 16,
    marginVertical: 4,
    marginHorizontal: 8,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  conversationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  userName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  channel: {
    fontSize: 14,
    color: '#667eea',
    fontWeight: '500',
  },
  conversationDetails: {
    marginBottom: 8,
  },
  followupDetails: {
    marginBottom: 8,
  },
  assigned: {
    fontSize: 14,
    color: '#666',
  },
  messageCount: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  contactInfo: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  messagePreview: {
    fontSize: 14,
    color: '#999',
    marginTop: 4,
    fontStyle: 'italic',
  },
  timestamp: {
    fontSize: 12,
    color: '#999',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
  },
});
