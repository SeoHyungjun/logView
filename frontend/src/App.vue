<script setup lang="ts">
import { ref, onMounted } from 'vue';

// 로그 항목의 타입을 정의합니다.
interface LogEntry {
  role: 'user' | 'assistant' | string; // 역할은 user 또는 assistant일 수 있습니다.
  content: string;
  [key: string]: any; // 그 외 추가적인 키가 있을 수 있습니다.
}

// 로그 데이터를 저장할 반응형 변수를 선언합니다.
const logs = ref<LogEntry[]>([]);
const error = ref<string | null>(null);

// 컴포넌트가 마운트(생성)될 때 실행될 함수입니다.
onMounted(async () => {
  try {
    // 백엔드 API에 로그 데이터를 요청합니다.
    const response = await fetch('http://127.0.0.1:8000/api/logs');
    if (!response.ok) {
      throw new Error('서버에서 데이터를 가져오는 데 실패했습니다.');
    }
    const data = await response.json();
    if (data.error) {
      throw new Error(data.error);
    }
    logs.value = data;
  } catch (e: any) {
    console.error(e);
    error.value = `로그를 불러올 수 없습니다: ${e.message}`;
  }
});
</script>

<template>
  <div id="log-viewer-container">
    <header>
      <h1>LLM Log Viewer</h1>
    </header>
    <main class="chat-container">
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
      <div v-else-if="logs.length === 0" class="loading-message">
        로그를 불러오는 중입니다...
      </div>
      <div v-for="(log, index) in logs" :key="index" :class="['message-row', log.role]">
        <div class="message-bubble">
          <div class="role">{{ log.role }}</div>
          <div class="content">{{ log.content }}</div>
        </div>
      </div>
    </main>
  </div>
</template>

<style>
/* 전체적인 앱 스타일 */
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  background-color: #f0f2f5;
  margin: 0;
  padding: 0;
  display: flex;
  justify-content: center;
}

#app {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

#log-viewer-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

header {
  background-color: #ffffff;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #dcdcdc;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  z-index: 10;
}

header h1 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.chat-container {
  flex-grow: 1;
  padding: 2rem;
  overflow-y: auto;
  background-color: #f0f2f5;
}

/* 메시지 스타일 */
.message-row {
  display: flex;
  margin-bottom: 1rem;
}

.message-bubble {
  max-width: 70%;
  padding: 0.8rem 1rem;
  border-radius: 18px;
  color: #222;
}

.message-bubble .role {
  font-weight: bold;
  font-size: 0.8rem;
  margin-bottom: 0.3rem;
  text-transform: capitalize;
}

.message-bubble .content {
  white-space: pre-wrap; /* 줄바꿈을 인식합니다. */
  word-wrap: break-word;
}

/* 유저 메시지 스타일 */
.message-row.user {
  justify-content: flex-end;
}

.message-row.user .message-bubble {
  background-color: #0084ff;
  color: white;
  border-bottom-right-radius: 4px;
}

.message-row.user .message-bubble .role {
  color: #e0f7ff;
}

/* 어시스턴트 메시지 스타일 */
.message-row.assistant {
  justify-content: flex-start;
}

.message-row.assistant .message-bubble {
  background-color: #ffffff;
  border: 1px solid #e0e0e0;
  border-bottom-left-radius: 4px;
}

.message-row.assistant .message-bubble .role {
  color: #555;
}

/* 에러 및 로딩 메시지 */
.error-message, .loading-message {
  text-align: center;
  padding: 2rem;
  color: #888;
  font-size: 1rem;
}
</style>