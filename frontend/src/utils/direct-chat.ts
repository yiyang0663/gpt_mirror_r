import { MessagePlugin } from 'tdesign-vue-next';

import { useUserStore } from '@/store';

export interface MirrorTokenItem {
  id?: number;
  chatgpt_username?: string;
  mirror_token?: string;
  proxy_mirror_token?: string;
  web_proxy_token?: string;
  auth_status?: boolean;
  plan_type?: string;
  account_type?: string;
  source_type?: string;
}

export interface ConsumerChatEntry {
  token: string;
  id: number | null;
  chatgpt_username: string;
  plan_type: string;
  account_type: string;
  source_type: string;
}

export const defaultConsumerModels = ['gpt-4o-mini', 'gpt-4o', 'gpt-4'];

const redirectToLogin = () => {
  window.location.hash = '#/login';
};

const buildAuthorizedHeaders = () => {
  const userStore = useUserStore();
  return {
    'Content-Type': 'application/json',
    Authorization: `token ${userStore.token}`,
  };
};

const readErrorMessage = async (response: Response) => {
  try {
    const errorData = await response.json();
    if (errorData?.message) {
      return String(errorData.message);
    }
  } catch (error) {
    console.error(error);
  }
  return '';
};

export const fetchConsumerTokenList = async (model = ''): Promise<MirrorTokenItem[] | null> => {
  const query = model ? `?model=${encodeURIComponent(model)}` : '';
  const response = await fetch(`/0x/user/get-mirror-token${query}`, {
    method: 'GET',
    headers: buildAuthorizedHeaders(),
  });

  if (response.status === 401 || response.status === 403) {
    redirectToLogin();
    return null;
  }

  if (response.status === 500) {
    MessagePlugin.error('系统异常');
    return null;
  }

  if (response.status === 502) {
    MessagePlugin.error('服务未正常启动');
    return null;
  }

  if (!response.ok) {
    MessagePlugin.error((await readErrorMessage(response)) || '获取对话入口失败');
    return null;
  }

  try {
    return await response.json();
  } catch (error) {
    console.error(error);
    MessagePlugin.error('获取对话入口失败');
    return null;
  }
};

export const getConsumerChatEntry = async (model = ''): Promise<ConsumerChatEntry | null> => {
  const tokenList = await fetchConsumerTokenList(model);
  if (!tokenList?.length) {
    MessagePlugin.error('当前账号暂未分配可用的对话通道，请联系管理员');
    return null;
  }

  const activeItem = tokenList.find(
    (item) => item?.auth_status !== false && (item.web_proxy_token || item.proxy_mirror_token || item.mirror_token),
  );
  const token = activeItem?.web_proxy_token || activeItem?.proxy_mirror_token || activeItem?.mirror_token || '';

  if (!activeItem || !token) {
    MessagePlugin.error('当前账号暂未分配可用的对话通道，请联系管理员');
    return null;
  }

  return {
    token,
    id: activeItem.id ?? null,
    chatgpt_username: activeItem.chatgpt_username || '',
    plan_type: activeItem.plan_type || '',
    account_type: activeItem.account_type || '',
    source_type: activeItem.source_type || '',
  };
};

export const redirectToConsumerChat = async () => {
  window.location.hash = '#/customer/chat';
  return true;
};
