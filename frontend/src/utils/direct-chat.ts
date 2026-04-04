import { MessagePlugin } from 'tdesign-vue-next';

import RequestApi from '@/api/request';

interface MirrorTokenItem {
  mirror_token?: string;
  auth_status?: boolean;
}

export const redirectToConsumerChat = async () => {
  const response = await RequestApi('/0x/user/get-mirror-token');
  if (!response.ok) {
    return false;
  }

  let data: MirrorTokenItem[] = [];
  try {
    data = await response.json();
  } catch (error) {
    MessagePlugin.error('获取对话入口失败');
    return false;
  }

  const activeToken = data.find((item) => item?.mirror_token && item.auth_status !== false);
  if (!activeToken?.mirror_token) {
    MessagePlugin.error('当前账号暂未分配可用的对话通道，请联系管理员');
    return false;
  }

  window.location.href = `/api/not-login?user_gateway_token=${encodeURIComponent(activeToken.mirror_token)}`;
  return true;
};
