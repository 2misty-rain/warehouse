<template>
  <div class="ai-assistant">
    <el-card class="chat-card">
      <template #header>
        <div class="card-header">
          <span>AI智能助手</span>
          <el-button size="small" @click="clearChat" type="danger" plain>
            <el-icon><Delete /></el-icon> 清空记录
          </el-button>
        </div>
      </template>

      <div class="chat-container">
        <!-- 快捷建议 -->
        <div class="quick-suggestions" v-if="messages.length <= 1">
          <div class="suggestion-section">
            <div class="suggestion-section-title">📊 查询分析</div>
            <el-tag
              v-for="(suggestion, index) in quickSuggestions.filter(s => s.type === 'query')"
              :key="'q-' + index"
              class="suggestion-tag"
              @click="useSuggestion(suggestion.text)"
              effect="plain"
            >
              {{ suggestion.text }}
            </el-tag>
          </div>
          <div class="suggestion-section" style="margin-top: 10px;">
            <div class="suggestion-section-title">⚡ 快捷操作</div>
            <el-tag
              v-for="(suggestion, index) in quickSuggestions.filter(s => s.type === 'operation')"
              :key="'o-' + index"
              class="suggestion-tag suggestion-tag-operation"
              @click="useSuggestion(suggestion.text)"
              effect="plain"
            >
              {{ suggestion.text }}
            </el-tag>
          </div>
        </div>

        <div class="messages" ref="messagesContainer">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            :class="['message', msg.sender]"
          >
            <div class="message-content">
              <div v-if="msg.type === 'text'" style="white-space: pre-wrap;">{{ msg.content }}</div>
              <div v-else-if="msg.type === 'action'" class="action-message">
                <p><strong>操作:</strong> {{ msg.action }}</p>
                <p><strong>详情:</strong> {{ msg.details }}</p>
              </div>
            </div>
            <div class="message-time">{{ msg.time }}</div>
          </div>
        </div>

        <div class="input-area">
          <el-input
            v-model="inputMessage"
            placeholder="请输入您的问题，例如：当前库存情况如何？"
            :rows="3"
            type="textarea"
            @keyup.enter="sendMessage"
          />
          <el-button
            type="primary"
            @click="sendMessage"
            :loading="sending"
            style="margin-top: 10px;"
          >
            发送
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted, nextTick } from 'vue';
import { aiAPI } from '../api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Delete } from '@element-plus/icons-vue';

export default {
  name: 'AIAssistant',
  components: { Delete },
  setup() {
    // 从localStorage加载历史消息
    const loadMessages = () => {
      try {
        const saved = localStorage.getItem('ai_chat_messages');
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed && parsed.length > 0) {
            return parsed;
          }
        }
      } catch (e) {
        console.error('加载聊天记录失败:', e);
      }
      return [
        {
          sender: 'ai',
          type: 'text',
          content: '您好！我是智能库存管理助手，可以帮您分析库存数据、提供管理建议。请问有什么可以帮助您的？',
          time: new Date().toLocaleTimeString()
        }
      ];
    };

    const messages = ref(loadMessages());
    const inputMessage = ref('');
    const sending = ref(false);
    const messagesContainer = ref(null);

    // 快捷建议列表
    const quickSuggestions = ref([
      { text: '当前库存情况如何？', type: 'query' },
      { text: '截止到现在卖了多少台设备？', type: 'query' },
      { text: '本周出库了多少设备？', type: 'query' },
      { text: '有哪些设备逾期未还？', type: 'query' },
      { text: '设备 DEV001 给某客户试用了，预计下周五还回', type: 'operation' },
      { text: '设备 DEV001 的物联网卡开卡了', type: 'operation' },
    ]);

    // 从后端加载动态建议
    const loadDynamicSuggestions = async () => {
      try {
        const res = await aiAPI.getSuggestions();
        if (res.success && res.suggestions?.length > 0) {
          quickSuggestions.value = res.suggestions;
        }
      } catch (e) {
        // 保持默认建议
      }
    };

    // 使用快捷建议
    const useSuggestion = (suggestion) => {
      inputMessage.value = suggestion;
      sendMessage();
    };

    // 保存消息到localStorage
    const saveMessages = () => {
      try {
        // 只保留最近100条消息，避免localStorage过大
        const toSave = messages.value.slice(-100);
        localStorage.setItem('ai_chat_messages', JSON.stringify(toSave));
      } catch (e) {
        console.error('保存聊天记录失败:', e);
      }
    };

    const scrollToBottom = () => {
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
        }
      });
    };

    const addMessage = (sender, type, content, time = new Date().toLocaleTimeString()) => {
      messages.value.push({
        sender,
        type,
        content,
        time
      });
      saveMessages(); // 每次添加消息后保存
      scrollToBottom();
    };

    const sendMessage = async () => {
      if (!inputMessage.value.trim() || sending.value) return;

      const userMessage = inputMessage.value.trim();

      // 添加用户消息
      addMessage('user', 'text', userMessage);
      inputMessage.value = '';
      sending.value = true;

      try {
        // 使用新的智能对话接口
        const response = await aiAPI.chat({ user_input: userMessage });

        console.log('AI回复:', response); // 调试日志

        if (response.error) {
          addMessage('ai', 'text', `抱歉，出现错误：${response.error}`);
        } else if (response.success && response.reply) {
          // 新版 Agent: 直接返回结果，无需确认
          addMessage('ai', 'text', response.reply);
          // 操作成功触发数据刷新
          window.dispatchEvent(new CustomEvent('ai-data-changed'));
        } else if (response.reply) {
          addMessage('ai', 'text', response.reply);
        } else {
          addMessage('ai', 'text', '操作完成');
        }
      } catch (error) {
        console.error('AI对话失败:', error);
        addMessage('ai', 'text', `处理失败: ${error.message || '未知错误'}`);
      } finally {
        sending.value = false;
      }
    };

    // 显示操作确认对话框
    const showActionConfirm = (action, params, aiReply) => {
      const actionNames = {
        'create_inventory': '添加设备',
        'batch_create_inventory': '批量添加设备',
        'batch_create_inventory_range': '批量添加范围设备',
        'update_inventory': '更新设备',
        'delete_inventory': '删除设备',
        'create_borrow': '借出设备',
        'return_borrow': '归还设备',
        'sell_device': '销售出库',
        'smart_assign_device': '智能设备分配',
        'update_iot_card': '更新IoT卡状态'
      };
      
      const actionName = actionNames[action] || action;
      
      ElMessageBox.confirm(
        `AI建议执行以下操作：\n\n${aiReply}\n\n是否确认执行"${actionName}"操作？`,
        '确认操作',
        {
          confirmButtonText: '确认执行',
          cancelButtonText: '取消',
          type: 'warning',
          distinguishCancelAndClose: true
        }
      ).then(async () => {
        // 用户确认，执行操作
        await executeAiAction(action, params);
      }).catch((action) => {
        if (action === 'cancel') {
          addMessage('ai', 'text', '❌ 操作已取消');
        }
      });
    };

    // 执行AI生成的操作
    const executeAiAction = async (action, params) => {
      try {
        // 找到最后一条用户消息用于日志记录
        const lastUserMsg = [...messages.value].reverse().find(m => m.sender === 'user');
        const result = await aiAPI.executeAction({
          action,
          params,
          user_input: lastUserMsg?.content || ''
        });

        if (result.success) {
          addMessage('ai', 'text', result.message || '✅ 操作成功');
          ElMessage.success(result.message || '操作成功');
        } else if (result.needs_return_date) {
          addMessage('ai', 'text', `⏳ ${result.message || '请提供归还日期'}`);
          ElMessage.warning('请补充归还日期信息');
        } else {
          const errDetail = result.detail || result.message || '未知错误';
          addMessage('ai', 'text', `❌ 操作失败: ${errDetail}`);
          ElMessage.error(errDetail);
        }
      } catch (error) {
        console.error('执行操作失败:', error);
        const errMsg = error.response?.data?.detail || error.message || '未知错误';
        addMessage('ai', 'text', `❌ 执行失败: ${errMsg}`);
        ElMessage.error('执行失败');
      }
    };

    const clearChat = () => {
      ElMessageBox.confirm(
        '确定要清空所有聊天记录吗？此操作不可恢复。',
        '确认清空',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        }
      ).then(() => {
        messages.value = [
          {
            sender: 'ai',
            type: 'text',
            content: '您好！我是智能库存管理助手，可以帮您分析库存数据、提供管理建议。请问有什么可以帮助您的？',
            time: new Date().toLocaleTimeString()
          }
        ];
        saveMessages();
        ElMessage.success('聊天记录已清空');
      }).catch(() => {
        // 用户取消
      });
    };

    onMounted(() => {
      scrollToBottom();
      loadDynamicSuggestions();
    });

    return {
      messages,
      inputMessage,
      sending,
      messagesContainer,
      quickSuggestions,
      sendMessage,
      clearChat,
      useSuggestion,
      showActionConfirm,
      executeAiAction
    };
  }
};
</script>

<style scoped>
.ai-assistant {
  padding: 20px;
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.chat-card {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 快捷建议样式 */
.quick-suggestions {
  padding: 15px;
  margin-bottom: 15px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  color: white;
}

.suggestion-section-title {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 6px;
}

.suggestion-tag {
  margin: 5px;
  cursor: pointer;
  transition: all 0.3s;
  background-color: rgba(255, 255, 255, 0.2) !important;
  border-color: rgba(255, 255, 255, 0.3) !important;
  color: white !important;
}

.suggestion-tag:hover {
  background-color: rgba(255, 255, 255, 0.3) !important;
  transform: translateY(-2px);
}

.suggestion-tag-operation {
  background-color: rgba(255, 193, 7, 0.25) !important;
  border-color: rgba(255, 193, 7, 0.4) !important;
}

.suggestion-tag-operation:hover {
  background-color: rgba(255, 193, 7, 0.4) !important;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  margin-bottom: 20px;
  background-color: #fafafa;
}

.message {
  margin-bottom: 15px;
  max-width: 80%;
}

.message.user {
  margin-left: auto;
  text-align: right;
}

.message.ai {
  margin-right: auto;
  text-align: left;
}

.message-content {
  display: inline-block;
  padding: 10px 15px;
  border-radius: 10px;
  margin-bottom: 5px;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.message.user .message-content {
  background-color: #409EFF;
  color: white;
}

.message.ai .message-content {
  background-color: #f0f2f5;
  color: #303133;
}

.action-message p {
  margin: 5px 0;
}

.message-time {
  font-size: 12px;
  color: #909399;
  text-align: right;
}

.input-area {
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dialog-footer {
  text-align: right;
}
</style>
