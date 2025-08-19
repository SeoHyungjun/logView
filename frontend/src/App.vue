<script setup lang="ts">
import { ref, computed, onMounted, nextTick, Directive } from 'vue';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';

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

interface LogPart {
  type: 'text' | 'code';
  content: string;
  lang?: string;
}

interface SessionData {
  accumulated_conversations: any[];
  expected_results: string[];
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

const API_BASE_URL = 'http://localhost:8000';

const logs = computed(() => activeSessionData.value?.accumulated_conversations || []);

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

const getExpectedResultFor = (currentIndex: number) => {
  if (!activeSessionData.value || !activeSessionData.value.expected_results) return null;
  const assistantMsgIndex = logs.value.slice(0, currentIndex).filter(l => l.role === 'assistant').length;
  return activeSessionData.value.expected_results[assistantMsgIndex];
};

// --- 이벤트 핸들러 ---
const handleFileSelect = (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (input.files) {
    uploadFiles(Array.from(input.files));
    input.value = '';
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
onMounted(() => { fetchTree(); });

// --- 코드 하이라이팅 ---
const processLogContent = computed(() => {
  return (content: string): LogPart[] => {
    if (typeof content !== 'string') return [];
    const parts: LogPart[] = [];
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)\n```/g;
    let lastIndex = 0;
    let match;
    while ((match = codeBlockRegex.exec(content)) !== null) {
      const [fullMatch, lang, code] = match;
      if (match.index > lastIndex) parts.push({ type: 'text', content: content.substring(lastIndex, match.index) });
      parts.push({ type: 'code', content: code, lang: lang || 'plaintext' });
      lastIndex = match.index + fullMatch.length;
    }
    if (lastIndex < content.length) parts.push({ type: 'text', content: content.substring(lastIndex) });
    return parts;
  };
});

const vHighlight: Directive<HTMLElement, { content: string; lang?: string }> = {
  mounted: (el, binding) => highlight(el, binding.value),
  updated: (el, binding) => highlight(el, binding.value),
};

const highlight = (el: HTMLElement, binding: { content: string; lang?: string }) => {
  el.innerHTML = binding.content;
  if (binding.lang) el.className = `language-${binding.lang}`;
  nextTick(() => { hljs.highlightElement(el); });
};

</script>

<template>
  <div v-if="treeData.length === 0 && !isLoading" class="init-page-container" @dragover.prevent="isDraggingOver = true" @dragleave.prevent="isDraggingOver = false" @drop="handleDrop">
    <div class="init-content-wrapper">
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
      <input type="file" ref="fileInput" @change="handleFileSelect" style="display: none;" multiple accept=".jsonl" />
      <input type="file" ref="folderInput" @change="handleFileSelect" style="display: none;" webkitdirectory />
    </div>
  </div>

  <div v-else class="app-layout">
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
    </div>

    <div class="chat-panel">
      <div class="chat-container">
        <div v-if="isLoading" class="message"><p class="loading-message">로딩 중...</p></div>
        <div v-else-if="error" class="message"><p class="error-message">{{ error }}</p></div>
        <div v-else-if="logs.length === 0 && flattenedTree.length > 0" class="message"><p class="loading-message">왼쪽 목록에서 대화 세션을 선택하세요.</p></div>
        <div v-else-if="logs.length === 0 && flattenedTree.length === 0" class="message"><p class="loading-message">표시할 로그가 없습니다. 파일을 업로드하세요.</p></div>
        <div v-else>
          <div v-for="(log, index) in logs" :key="index" :class="['message', `role-${log.role}`]">
            <div class="bubble">
              <div class="content">
                <template v-for="(part, pIndex) in processLogContent(log.content)" :key="pIndex">
                  <pre v-if="part.type === 'code'"><code v-highlight="{ content: part.content, lang: part.lang }"></code></pre>
                  <p v-else v-html="part.content.replace(/\n/g, '<br>')"></p>
                </template>
              </div>
            </div>
            <div v-if="log.role === 'assistant'" class="expected-result">
              <div class="expected-title">Expected Result</div>
              <div class="expected-content">{{ getExpectedResultFor(index) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="ghost-panel"></div>
  </div>
</template>

<style>
/* 스타일은 이전과 동일합니다 */
.init-page-container { display: flex; align-items: center; justify-content: center; height: 100vh; padding: 2rem; box-sizing: border-box; text-align: center; }
.init-content-wrapper { max-width: 720px; width: 100%; }
.init-title { font-size: 3.2rem; font-weight: 700; color: #2c3e50; margin-bottom: 1rem; }
.init-description { font-size: 1.1rem; color: #5a6a7a; margin-bottom: 2.5rem; }
.drop-zone { width: 100%; border: 2px dashed #ccc; border-radius: 16px; padding: 2rem 3rem; transition: background-color 0.3s, border-color 0.3s; box-sizing: border-box; }
.drop-zone.is-dragging-over { background-color: #e8f0fe; border-color: #4285f4; }
.drop-zone-content { text-align: center; color: #555; }
.drop-zone-content svg { color: #aaa; margin-bottom: 0.75rem; }
.drop-zone-content p { font-size: 1.1rem; margin: 0.5rem 0; }
.or-text { color: #999; margin: 1.25rem 0 !important; }
.button-group { display: inline-flex; border: 1px solid #007aff; border-radius: 8px; overflow: hidden; }
.select-button { background-color: white; color: #007aff; border: none; padding: 0.7rem 1.5rem; font-size: 1rem; font-weight: 500; cursor: pointer; transition: background-color 0.2s; }
.select-button:hover { background-color: #f0f8ff; }
.select-button:first-child { border-right: 1px solid #007aff; }
.app-layout { display: flex; justify-content: space-between; height: 100vh; width: 100%; }
.file-panel { width: 320px; flex-shrink: 0; background-color: #f7f7f7; border-right: 1px solid #e0e0e0; display: flex; flex-direction: column; transition: background-color 0.3s; }
.file-panel.is-dragging-over { background-color: #e8f0fe; }
.file-list { list-style: none; padding: 0; margin: 0; overflow-y: auto; flex-grow: 1; user-select: none; }
.file-item { display: flex; align-items: center; cursor: pointer; padding-top: 0.5rem; padding-bottom: 0.5rem; border-bottom: 1px solid #e8e8e8; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; position: relative; }
.file-item:hover { background-color: #eef5ff; }
.file-item.active { background-color: #d4e8ff; }
.item-icon { margin-right: 8px; font-size: 0.8em; width: 12px; text-align: center; }
.item-name { flex-grow: 1; }
.close-button { color: #ccc; font-weight: bold; cursor: pointer; padding: 0 8px; font-size: 1.2rem; line-height: 1; position: absolute; right: 5px; display: none; }
.file-item:hover .close-button { display: block; }
.close-button:hover { color: #888; }
.empty-list-message { color: #888; text-align: center; padding: 1rem; }
.chat-panel { flex-grow: 1; overflow-y: auto; display: flex; justify-content: center; }
.chat-container { width: 100%; max-width: 960px; padding: 2rem 1rem; box-sizing: border-box; }
.message + .message { margin-top: 1.5rem; }
.message.role-user + .message.role-assistant { margin-top: 2.5rem; }
.message.role-assistant + .message.role-user { margin-top: 2.5rem; }
.message { display: flex; flex-direction: column; }
.message.role-user { align-items: flex-end; }
.message.role-assistant { align-items: flex-start; }
.bubble { padding: 0.8rem 1.2rem; border-radius: 1.2rem; max-width: 85%; display: inline-block;}
.message.role-user .bubble { background-color: #f0f0f0; }
.message.role-assistant .bubble { background-color: transparent; border: 1px solid #e0e0e0;}
.content { white-space: pre-wrap; word-wrap: break-word; line-height: 1.6; }
.error-message, .loading-message { text-align: center; padding: 2rem; color: #888; }
.ghost-panel { width: 320px; flex-shrink: 0; }
pre code { display: block; overflow-x: auto; padding: 1em; background: #2d2d2d; color: #ccc; border-radius: 8px; }
.message.role-assistant .bubble pre code { background-color: #2d2d2d; }
.message.role-user .bubble pre code { background-color: #3a3a3a; }
.content p { margin-bottom: 1em; }
.content p:last-child { margin-bottom: 0; }
.content pre { margin-top: 1em; margin-bottom: 1em; }
.content pre:first-child { margin-top: 0; }
.content pre:last-child { margin-bottom: 0; }

.expected-result {
  border: 1px solid #a2d2ff;
  background-color: #f0f8ff;
  border-radius: 8px;
  padding: 0.8rem 1.2rem;
  margin-top: 0.5rem;
  max-width: 85%;
  font-size: 0.9em;
}
.expected-title {
  font-weight: bold;
  color: #0077cc;
  margin-bottom: 0.5rem;
}
.expected-content {
  color: #333;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>