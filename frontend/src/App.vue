<script setup lang="ts">
import { ref, onMounted } from 'vue';

// --- 상태 관리 ---
interface LogEntry {
  role: 'user' | 'assistant' | string;
  content: string;
  [key: string]: any;
}
const logs = ref<LogEntry[]>([]);
const error = ref<string | null>(null);
const fileList = ref<File[]>([]);

// --- 데이터 로딩 ---
onMounted(async () => {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/logs');
    if (!response.ok) throw new Error('Server response was not ok.');
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    logs.value = data;
  } catch (e: any) {
    console.error(e);
    error.value = `Failed to load logs: ${e.message}`;
  }
});

// --- 이벤트 핸들러 ---
const handleDirectoryChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (input.files) {
    fileList.value = Array.from(input.files);
  }
};
</script>

<template>
  <div class="app-layout">
    <!-- 1. 왼쪽 파일 패널 -->
    <div class="file-panel">
      <div class="file-panel-header">
        <label for="dir-picker" class="dir-picker-label">폴더 선택</label>
        <input type="file" id="dir-picker" webkitdirectory directory multiple @change="handleDirectoryChange" style="display: none;"/>
      </div>
      <ul class="file-list">
        <li v-if="fileList.length === 0" class="empty-list-message">폴더를 선택하세요.</li>
        <li v-for="file in fileList" :key="file.name" class="file-item">{{ file.name }}</li>
      </ul>
    </div>

    <!-- 2. 중앙 채팅 패널 -->
    <div class="chat-panel">
      <div class="chat-container">
        <div v-if="error" class="message"><p class="error-message">{{ error }}</p></div>
        <div v-else-if="logs.length === 0" class="message"><p class="loading-message">Loading logs...</p></div>
        <div v-else>
          <div v-for="(log, index) in logs" :key="index" :class="['message', `role-${log.role}`]">
            <div class="bubble"><div class="content">{{ log.content }}</div></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 오른쪽 유령 패널 (중앙 정렬용) -->
    <div class="ghost-panel"></div>
  </div>
</template>

<style>
/* --- 전체 레이아웃 --- */
.app-layout {
  display: flex;
  justify-content: space-between; /* 양쪽 끝으로 요소를 분산 */
  height: 100vh;
  width: 100%;
}

/* --- 1. 왼쪽 파일 패널 --- */
.file-panel {
  width: 320px;
  flex-shrink: 0;
  background-color: #f7f7f7;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
}
.file-panel-header {
  padding: 1rem;
  border-bottom: 1px solid #e0e0e0;
  text-align: center;
}
.dir-picker-label {
  background-color: #007aff;
  color: white;
  padding: 0.6rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
}
.file-list {
  list-style: none;
  padding: 0;
  margin: 0;
  overflow-y: auto;
  flex-grow: 1;
}
.file-item, .empty-list-message {
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid #e8e8e8;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.empty-list-message { color: #888; text-align: center; }

/* --- 2. 중앙 채팅 패널 --- */
.chat-panel {
  flex-grow: 1; /* 남는 공간을 모두 차지 */
  overflow-y: auto;
  display: flex;
  justify-content: center;
}
.chat-container {
  width: 100%; /* chat-panel 안에서 꽉 참 */
  max-width: 960px;
  padding: 2rem 1rem;
  box-sizing: border-box;
}
.message {
  display: flex;
  /* 기존의 일관된 margin-bottom을 제거하고, 아래의 규칙으로 대체합니다. */
}

/* 기본 메시지 간격 (어시스턴트->어시스턴트, 사용자->사용자) */
.message + .message {
  margin-top: 1.5rem;
}

/* 사용자 -> 어시스턴트 답변 쌍의 간격을 좁힙니다. */
.message.role-user + .message.role-assistant {
  margin-top: 0.75rem;
}

/* 답변 쌍 사이의 간격(어시스턴트 -> 사용자)을 넓힙니다. */
.message.role-assistant + .message.role-user {
  margin-top: 2.5rem;
}
.message.role-user { justify-content: flex-end; }
.message.role-assistant { justify-content: flex-start; }
.bubble { padding: 0.8rem 1.2rem; border-radius: 1.2rem; max-width: 85%; }
.message.role-user .bubble { background-color: #f0f0f0; }
.message.role-assistant .bubble { background-color: transparent; text-align: left; }
.content { white-space: pre-wrap; word-wrap: break-word; line-height: 1.6; }
.error-message, .loading-message { text-align: center; padding: 2rem; color: #888; }

/* --- 3. 오른쪽 유령 패널 --- */
.ghost-panel {
  width: 320px; /* 왼쪽 패널과 동일한 너비 */
  flex-shrink: 0;
}
</style>