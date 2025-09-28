<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';

// --- 타입 정의 ---
interface TreeItem {
  id: string;
  name: string;
  type: 'file' | 'folder' | 'session';
  path: string;
  depth: number;
  isExpanded: boolean;
  children: TreeItem[];
  sessionIndex?: number;
}

interface SessionData {
  accumulated_conversations: any[];
  expected_results: string[];
  criteria: string[];
  [key: string]: any;
}

// --- 상태 관리 ---
const activeSessionData = ref<SessionData | null>(null);
const error = ref<string | null>(null);
const treeData = ref<TreeItem[]>([]);
const isDraggingOver = ref(false);
const isDraggingOverPanel = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);
const folderInput = ref<HTMLInputElement | null>(null);
const activeSessionId = ref<string | null>(null);
const isLoading = ref(false);
const isPanelCollapsed = ref(false);

const API_BASE_URL = 'http://localhost:8000';

const logs = computed(() => activeSessionData.value?.accumulated_conversations || []);

// --- 마크다운 설정 (markdown-it) ---
const md = new MarkdownIt({
  html: true,
  breaks: true,
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return (
          '<pre class="hljs"><code>' +
          hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
          '</code></pre>'
        );
      } catch (__) {}
    }
    return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>';
  },
});

const renderMarkdown = (content: string) => {
  if (typeof content !== 'string') return '';
  return md.render(content);
};

// --- API 통신 ---
const fetchTree = async () => {
  try {
    isLoading.value = true;
    error.value = null;
    const response = await fetch(`${API_BASE_URL}/api/files`);
    if (!response.ok) throw new Error('파일 목록을 불러오는 데 실패했습니다.');
    const rawTree = await response.json();
    treeData.value = enhanceTree(rawTree);
  } catch (e: any) {
    error.value = e.message;
  } finally {
    isLoading.value = false;
  }
};

const fetchLogContent = async (item: TreeItem) => {
  if (item.type !== 'session') return;
  try {
    isLoading.value = true;
    error.value = null;
    activeSessionData.value = null;
    const response = await fetch(`${API_BASE_URL}/api/logs/${item.path}?session=${item.sessionIndex}`);
    if (!response.ok) throw new Error(`로그 파일을 불러오는 데 실패했습니다: ${item.name}`);
    activeSessionData.value = await response.json();
    activeSessionId.value = item.id;
  } catch (e: any) {
    error.value = e.message;
    activeSessionData.value = null;
  } finally {
    isLoading.value = false;
  }
};

const uploadFiles = async (files: File[]) => {
  if (files.length === 0) return;
  const formData = new FormData();
  const jsonlFiles = files.filter(file => file.name.endsWith('.jsonl'));
  if (jsonlFiles.length === 0) {
    error.value = "선택된 파일이나 폴더에 .jsonl 파일이 없습니다.";
    return;
  }
  jsonlFiles.forEach(file => {
    const filePath = (file as any).webkitRelativePath || file.name;
    formData.append('files', file, filePath);
  });
  try {
    isLoading.value = true;
    error.value = null;
    const response = await fetch(`${API_BASE_URL}/api/upload`, { method: 'POST', body: formData });
    if (!response.ok) throw new Error('파일 업로드에 실패했습니다.');
    await fetchTree();
    const firstSession = findFirstSession(treeData.value);
    if (firstSession) await fetchLogContent(firstSession);
  } catch (e: any) {
    error.value = e.message;
  } finally {
    isLoading.value = false;
  }
};

const deleteItem = async (item: TreeItem) => {
  if (!confirm(`'${item.name}'을(를) 정말 삭제하시겠습니까?`)) return;
  try {
    isLoading.value = true;
    error.value = null;
    const response = await fetch(`${API_BASE_URL}/api/files/${item.path}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('삭제에 실패했습니다.');
    const wasActive = activeSessionId.value?.startsWith(item.id);
    await fetchTree();
    if (wasActive) {
      activeSessionData.value = null;
      activeSessionId.value = null;
      const firstSession = findFirstSession(treeData.value);
      if (firstSession) await fetchLogContent(firstSession);
    }
  } catch (e: any) {
    error.value = e.message;
  } finally {
    isLoading.value = false;
  }
};

// --- 유틸리티 함수 ---
const enhanceTree = (nodes: any[], depth = 0): TreeItem[] => {
  return nodes.map(node => ({ ...node, depth, isExpanded: true, children: node.children ? enhanceTree(node.children, depth + 1) : [] }));
};

const findFirstSession = (nodes: TreeItem[]): TreeItem | null => {
  for (const node of nodes) {
    if (node.type === 'session') return node;
    if (node.children) {
      const found = findFirstSession(node.children);
      if (found) return found;
    }
  }
  return null;
};

const flattenedTree = computed(() => {
  const flat: TreeItem[] = [];
  const traverse = (items: TreeItem[]) => {
    items.forEach(item => {
      flat.push(item);
      if (item.isExpanded && item.children) traverse(item.children);
    });
  };
  traverse(treeData.value);
  return flat;
});

const getAssistantTurnData = (currentIndex: number, dataKey: 'expected_results' | 'criteria') => {
  if (!activeSessionData.value || !activeSessionData.value[dataKey]) return null;
  const assistantMsgIndex = logs.value.slice(0, currentIndex).filter(l => l.role === 'assistant').length;
  return activeSessionData.value[dataKey][assistantMsgIndex];
};

// --- 이벤트 핸들러 ---
const handleFileSelect = (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (input.files) {
    uploadFiles(Array.from(input.files));
    input.value = '';
  }
};

const handleKeyDown = (event: KeyboardEvent) => {
  if (!activeSessionId.value) return;
  if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return;

  event.preventDefault();

  const currentIndex = flattenedTree.value.findIndex(item => item.id === activeSessionId.value);
  if (currentIndex === -1) return;

  let nextIndex = -1;

  if (event.key === 'ArrowDown') {
    for (let i = currentIndex + 1; i < flattenedTree.value.length; i++) {
      if (flattenedTree.value[i].type === 'session') {
        nextIndex = i;
        break;
      }
    }
  } else { // ArrowUp
    for (let i = currentIndex - 1; i >= 0; i--) {
      if (flattenedTree.value[i].type === 'session') {
        nextIndex = i;
        break;
      }
    }
  }

  if (nextIndex !== -1) {
    const nextSession = flattenedTree.value[nextIndex];
    fetchLogContent(nextSession);
  }
};

const traverseFileTree = async (item: any): Promise<File[]> => {
  const files: File[] = [];
  const queue: any[] = [item];
  while (queue.length > 0) {
    const entry = queue.shift();
    if (entry.isFile) {
      const file = await new Promise<File>(resolve => entry.file(resolve));
      if (file.name.endsWith('.jsonl')) {
        Object.defineProperty(file, 'webkitRelativePath', { value: entry.fullPath.substring(1) });
        files.push(file);
      }
    } else if (entry.isDirectory) {
      const reader = entry.createReader();
      const entries = await new Promise<any[]>(resolve => reader.readEntries(resolve));
      queue.push(...entries);
    }
  }
  return files;
};

const handleDrop = async (event: DragEvent) => {
  event.preventDefault();
  isDraggingOver.value = false;
  isDraggingOverPanel.value = false;
  if (event.dataTransfer?.items) {
    const allFiles: File[] = [];
    const items = Array.from(event.dataTransfer.items);
    for (const item of items) {
      const entry = item.webkitGetAsEntry();
      if (entry) {
        const files = await traverseFileTree(entry);
        allFiles.push(...files);
      }
    }
    if (allFiles.length > 0) await uploadFiles(allFiles);
  }
};

const onFileItemClick = (item: TreeItem) => {
  if (item.type === 'folder' || item.type === 'file') {
    item.isExpanded = !item.isExpanded;
  } else if (item.type === 'session') {
    fetchLogContent(item);
  }
};

// --- 생명주기 훅 ---
onMounted(() => {
  fetchTree();
  window.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
});

</script>

<template>
  <input type="file" ref="fileInput" @change="handleFileSelect" style="display: none;" multiple accept=".jsonl" />
  <input type="file" ref="folderInput" @change="handleFileSelect" style="display: none;" webkitdirectory />

  <div v-if="treeData.length === 0 && !isLoading" class="init-page-container">
    <div class="init-content-wrapper" @dragover.prevent="isDraggingOver = true" @dragleave.prevent="isDraggingOver = false" @drop="handleDrop">
      <h1 class="init-title">Log Viewer</h1>
      <p class="init-description">JSONL 형식의 로그 파일을 위한 간단한 뷰어입니다.</p>
      <div :class="['drop-zone', { 'is-dragging-over': isDraggingOver }]">
        <div class="drop-zone-content">
          <svg width="48" height="48" viewBox="0 0 16 16"><path fill="currentColor" d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/><path fill="currentColor" d="M7.646 1.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 2.707V11.5a.5.5 0 0 1-1 0V2.707L5.354 4.854a.5.5 0 1 1-.708-.708l3-3z"/></svg>
          <p>여기에 .jsonl 파일이나 폴더를 드래그 앤 드롭하세요.</p>
          <p class="or-text">또는</p>
          <div class="button-group">
            <button @click="fileInput?.click()" class="select-button">파일 선택</button>
            <button @click="folderInput?.click()" class="select-button">폴더 선택</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="app-layout" :class="{ 'panel-collapsed': isPanelCollapsed }">
    <div class="file-panel" :class="{ 'is-dragging-over': isDraggingOverPanel }" @dragover.prevent="isDraggingOverPanel = true" @dragleave.prevent="isDraggingOverPanel = false" @drop="handleDrop">
      <ul class="file-list">
        <li v-if="flattenedTree.length === 0 && !isLoading" class="empty-list-message">업로드된 파일이 없습니다.</li>
        <li v-for="item in flattenedTree" :key="item.id" class="file-item" :class="{ 'active': item.id === activeSessionId }" :style="{ paddingLeft: `${item.depth * 20 + 16}px` }" @click="onFileItemClick(item)">
          <span class="item-icon">
            <template v-if="item.type === 'folder'">{{ item.isExpanded ? '▼' : '▶' }}</template>
            <template v-else-if="item.type === 'file'">{{ item.isExpanded ? '▼' : '▶' }}</template>
            <template v-else-if="item.type === 'session'">💬</template>
            <template v-else>📄</template>
          </span>
          <span class="item-name">{{ item.name }}</span>
          <span v-if="item.type !== 'session'" class="close-button" @click.stop="deleteItem(item)">×</span>
        </li>
      </ul>
      <div class="panel-footer">
        <div class="button-group">
          <button @click="fileInput?.click()" class="select-button">파일 추가</button>
          <button @click="folderInput?.click()" class="select-button">폴더 추가</button>
        </div>
      </div>
    </div>

    <div class="panel-toggle-button" @click="isPanelCollapsed = !isPanelCollapsed">
      {{ isPanelCollapsed ? '▶' : '◀' }}
    </div>

    <div class="chat-panel">
      <div class="chat-container">
        <div v-if="isLoading" class="message-block"><p class="loading-message">로딩 중...</p></div>
        <div v-else-if="error" class="message-block"><p class="error-message">{{ error }}</p></div>
        <div v-else-if="logs.length === 0 && flattenedTree.length > 0" class="message-block"><p class="loading-message">왼쪽 목록에서 대화 세션을 선택하세요.</p></div>
        <div v-else-if="logs.length === 0 && flattenedTree.length === 0" class="message-block"><p class="loading-message">표시할 로그가 없습니다. 파일을 업로드하세요.</p></div>
        
        <template v-else v-for="(log, index) in logs" :key="index">
          <div v-if="log.role === 'user'" class="turn-card">
            <!-- Conversation Column -->
            <div class="conversation-pair">
              <!-- User Message -->
              <div :class="['message', `role-${log.role}`]">
                <div class="bubble">
                  <div class="content" v-html="renderMarkdown(log.content)"></div>
                </div>
              </div>

              <!-- Assistant Message -->
              <template v-if="index + 1 < logs.length && logs[index + 1].role === 'assistant'">
                <div :class="['message', `role-${logs[index + 1].role}`]">
                  <div class="bubble">
                    <div class="content" v-html="renderMarkdown(logs[index + 1].content)"></div>
                  </div>
                </div>
              </template>
            </div>

            <!-- Extra Info Column -->
            <div class="turn-extra">
              <template v-if="index + 1 < logs.length && logs[index + 1].role === 'assistant'">
                <div class="assistant-extra">
                  <div class="expected-result">
                    <div class="expected-title">Expected Result</div>
                    <div class="expected-content">{{ getAssistantTurnData(index + 1, 'expected_results') }}</div>
                  </div>
                  <div v-if="getAssistantTurnData(index + 1, 'criteria')" class="criteria-result">
                    <div class="criteria-title">Criteria</div>
                    <div class="criteria-content">{{ getAssistantTurnData(index + 1, 'criteria') }}</div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style>
:root {
  --border-color: #e0e0e0;
  --background-color: #f9fafb;
  --card-background-color: #ffffff;
  --card-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --panel-width: 320px;
}

body {
  background-color: var(--background-color);
}

/* Init Page Styles */
.init-page-container { display: flex; align-items: center; justify-content: center; height: 100vh; padding: 2rem; box-sizing: border-box; text-align: center; background-color: var(--background-color); }
.init-content-wrapper { max-width: 720px; width: 100%; }
.init-title { font-size: 3.2rem; font-weight: 700; color: #2c3e50; margin-bottom: 1rem; }
.init-description { font-size: 1.1rem; color: #5a6a7a; margin-bottom: 2.5rem; }
.drop-zone { width: 100%; border: 2px dashed #ccc; border-radius: 16px; padding: 2rem 3rem; transition: background-color 0.3s, border-color 0.3s; box-sizing: border-box; background-color: var(--card-background-color); }
.drop-zone.is-dragging-over { background-color: #e8f0fe; border-color: #4285f4; }
.drop-zone-content { text-align: center; color: #555; }
.drop-zone-content svg { color: #aaa; margin-bottom: 0.75rem; }
.drop-zone-content p { font-size: 1.1rem; margin: 0.5rem 0; }
.or-text { color: #999; margin: 1.25rem 0 !important; }
.button-group { display: flex; border: 1px solid #007aff; border-radius: 8px; overflow: hidden; }
.select-button { background-color: white; color: #007aff; border: none; padding: 0.7rem 1.5rem; font-size: 1rem; font-weight: 500; cursor: pointer; transition: background-color 0.2s; flex-grow: 1; }
.select-button:hover { background-color: #f0f8ff; }
.select-button:first-child { border-right: 1px solid #007aff; }

/* Main App Layout */
.app-layout { 
  display: flex;
  position: relative;
  height: 100vh;
  width: 100%;
  background-color: var(--background-color);
}

/* File Panel */
.file-panel { 
  width: var(--panel-width);
  flex-shrink: 0;
  background-color: var(--card-background-color);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease, padding 0.3s ease;
  overflow: hidden;
}
.app-layout.panel-collapsed .file-panel {
  width: 0;
  padding-left: 0;
  padding-right: 0;
  border-right: none;
}

.file-panel.is-dragging-over { background-color: #e8f0fe; }
.file-list { list-style: none; padding: 0; margin: 0; flex-grow: 1; user-select: none; white-space: nowrap; overflow-y: auto; }
.file-item { display: flex; align-items: center; cursor: pointer; padding: 0.5rem 1rem; border-bottom: 1px solid #f0f0f0; font-size: 0.9rem; overflow: hidden; text-overflow: ellipsis; position: relative; }
.file-item:hover { background-color: #eef5ff; }
.file-item.active { background-color: #d4e8ff; font-weight: 500; }
.item-icon { margin-right: 8px; font-size: 0.8em; width: 12px; text-align: center; }
.item-name { flex-grow: 1; }
.close-button { color: #ccc; font-weight: bold; cursor: pointer; padding: 0 8px; font-size: 1.2rem; line-height: 1; position: absolute; right: 5px; display: none; }
.file-item:hover .close-button { display: block; }
.close-button:hover { color: #888; }
.empty-list-message { color: #888; text-align: center; padding: 1rem; }

.panel-footer {
  padding: 1rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: center;
}

.panel-footer .button-group {
  width: 100%;
}

/* Chat Panel */
.chat-panel { 
  flex-grow: 1;
  overflow-y: auto;
  padding: 2rem;
  position: relative;
}

.panel-toggle-button {
  position: absolute;
  left: var(--panel-width);
  top: 50%;
  transform: translateY(-50%) translateX(-50%);
  background-color: white;
  border: 1px solid var(--border-color);
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 50%;
  font-size: 16px;
  color: #333;
  box-shadow: 0 0 10px rgba(0,0,0,0.1);
  transition: left 0.3s ease, background-color 0.2s ease;
  z-index: 10;
}
.app-layout.panel-collapsed .panel-toggle-button {
  left: 0;
}
.panel-toggle-button:hover { 
  background-color: #f0f0f0; 
}

.chat-container {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
}

.message-block {
  text-align: center;
  padding: 2rem;
  color: #888;
}

/* Turn Layout */
.turn-card {
  display: flex;
  gap: 2rem;
  background-color: var(--card-background-color);
  padding: 2rem;
  border-radius: 12px;
  box-shadow: var(--card-shadow);
  margin-bottom: 2rem;
}

.conversation-pair {
  flex: 3;
  min-width: 0;
}

.turn-extra {
  flex: 2;
  min-width: 0;
  border-left: 1px solid var(--border-color);
  padding-left: 2rem;
}

/* Message Bubbles & Content */
.message { display: flex; flex-direction: column; margin-bottom: 1rem; }
.message:last-child { margin-bottom: 0; }
.message.role-user { align-items: flex-end; }
.message.role-assistant { align-items: flex-start; }
.bubble { padding: 0.8rem 1.2rem; border-radius: 1.2rem; display: inline-block;}
.message.role-user .bubble { background-color: #f0f0f0; }
.message.role-assistant .bubble { background-color: transparent; }

.content {
  line-height: 1.6;
  word-wrap: break-word;
}

/* Markdown Content Styling */
.content p:last-child { margin-bottom: 0; }
.content pre {
  margin: 1em 0;
  border-radius: 8px;
  background-color: #f6f8fa;
  padding: 1.5em;
  overflow-x: auto;
}
.content pre code {
  background: none;
  padding: 0;
}
.content table {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
  overflow: hidden;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}
.content th, .content td {
  padding: 0.75rem 1rem;
  border: 1px solid var(--border-color);
  text-align: left;
}
.content th {
  background-color: #f7f7f7;
  font-weight: 600;
}
.content tbody tr:nth-of-type(even) {
  background-color: #fdfdfd;
}
.content blockquote {
  margin: 1em 0;
  padding: 0.5rem 1rem;
  border-left: 4px solid var(--border-color);
  background-color: #f7f7f7;
  color: #555;
}
.content ul, .content ol {
  padding-left: 1.5rem;
}

/* Assistant Extra Info */
.assistant-extra {
  width: 100%;
}

.expected-result, .criteria-result {
  border-radius: 8px;
  padding: 0.8rem 1.2rem;
  font-size: 0.9em;
  margin-bottom: 1rem;
  border: 1px solid transparent;
}

.expected-result {
  background-color: #f0f8ff;
  border-color: #a2d2ff;
}

.criteria-result {
  background-color: #fff0f0;
  border-color: #ffb3b3;
}

.expected-title, .criteria-title {
  font-weight: bold;
  margin-bottom: 0.5rem;
}

.expected-title { color: #0077cc; }
.criteria-title { color: #d92d20; }
.expected-content, .criteria-content {
  color: #333;
  white-space: pre-wrap;
  word-wrap: break-word;
}

</style>