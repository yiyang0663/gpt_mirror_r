import { ref } from 'vue';

import RequestApi from '@/api/request';

export interface CustomerConversationSummary {
  id: number;
  title: string;
  model_name: string;
  preview_text: string;
  message_count: number;
  last_message_at: number;
  created_time: number;
  updated_time: number;
}

export interface CustomerPersistedConversationMessage {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  account_label: string;
  sequence: number;
  created_time: number;
  updated_time: number;
}

export interface CustomerConversationDetail extends CustomerConversationSummary {
  messages: CustomerPersistedConversationMessage[];
}

const conversations = ref<CustomerConversationSummary[]>([]);
const activeConversationId = ref<number | null>(null);
const historyLoading = ref(false);

const sortConversations = (items: CustomerConversationSummary[]) => {
  return [...items].sort((left, right) => {
    if ((right.updated_time || 0) !== (left.updated_time || 0)) {
      return (right.updated_time || 0) - (left.updated_time || 0);
    }
    return right.id - left.id;
  });
};

const upsertConversationSummary = (payload: CustomerConversationSummary) => {
  const nextItem = { ...payload };
  const index = conversations.value.findIndex((item) => item.id === payload.id);
  if (index >= 0) {
    conversations.value.splice(index, 1, nextItem);
  } else {
    conversations.value.push(nextItem);
  }
  conversations.value = sortConversations(conversations.value);
};

const loadConversationList = async () => {
  historyLoading.value = true;
  try {
    const response = await RequestApi('/0x/user/chat-conversations');
    if (!response.ok) {
      return;
    }
    const payload = (await response.json()) as { results?: CustomerConversationSummary[] };
    conversations.value = sortConversations(payload.results || []);
  } finally {
    historyLoading.value = false;
  }
};

const resetConversationState = () => {
  conversations.value = [];
  activeConversationId.value = null;
  historyLoading.value = false;
};

export const useCustomerConversations = () => {
  return {
    conversations,
    activeConversationId,
    historyLoading,
    loadConversationList,
    resetConversationState,
    upsertConversationSummary,
  };
};
