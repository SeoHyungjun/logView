<script setup lang="ts">
import { ref, computed, nextTick, Directive } from 'vue';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css'; // 원하는 테마를 선택하세요

// --- 타입 정의 ---
interface TreeItem {
  id: string;
  name: string;
  type: 'file' | 'folder';
  depth: number;
  isExpanded: boolean;
  children: TreeItem[];
  file?: File;
}

interface LogPart {
  type: 'text' | 'code';
  content: string;
  lang?: string;
}

// --- 상태 관리 ---
const appStarted = ref(false);
const logs = ref<any[]>([]);
const error = ref<string | null>(null);
const treeData = ref<TreeItem[]>([]);
const isDraggingOver = ref(false);
const isDraggingOverPanel = ref(false); // 패널 드래그 상태
const fileInput = ref<HTMLInputElement | null>(null);
const folderInput = ref<HTMLInputElement | null>(null);
const activeFileId = ref<string | null>(null);

// --- 핵심 로직 ---
const startApp = () => { appStarted.value = true; };

const loadJsonlFile = async (file: File) => {
  try {
    error.value = null;
    logs.value = [];
    const content = await file.text();
    logs.value = content.split('\n').filter(line => line.trim() !== '').map(line => JSON.parse(line));
    const fileId = (file.webkitRelativePath || file.name);
    activeFileId.value = fileId.slice(0, fileId.indexOf(file.name) + file.name.length);
    
  } catch (e: any) {
    error.value = `파일을 파싱하는 중 오류 발생: ${e.message}`;
  }
};

const buildTree = (files: File[]): TreeItem[] => {
  const root: { [key: string]: any } = { children: {} };
  files.forEach(file => {
    const pathParts = (file.webkitRelativePath || file.name).split('/');
    let currentLevel = root.children;
    pathParts.forEach((part, index) => {
      if (!part) return;
      const isFolder = index < pathParts.length - 1;
      if (!currentLevel[part]) {
        currentLevel[part] = {
          id: (file.webkitRelativePath || file.name).slice(0, (file.webkitRelativePath || file.name).indexOf(part) + part.length),
          name: part, type: isFolder ? 'folder' : 'file', depth: index,
          isExpanded: true, children: isFolder ? {} : undefined, file: isFolder ? undefined : file,
        };
      }
      if (isFolder) { currentLevel = currentLevel[part].children; }
    });
  });
  const objectToTree = (node: { [key: string]: TreeItem }): TreeItem[] => {
    return Object.values(node).map(child => ({ ...child, children: child.children ? objectToTree(child.children as any) : [] }));
  };
  return objectToTree(root.children);
};

const processFiles = async (files: File[]) => {
  if (files.length === 0) return;
  const jsonlFiles = Array.from(files).filter(file => file.name.endsWith('.jsonl'));

  if (jsonlFiles.length === 0) {
    error.value = "선택된 파일이나 폴더에 .jsonl 파일이 없습니다.";
    if (!appStarted.value) { startApp(); }
    return;
  }

  const newTreeData = buildTree(jsonlFiles);
  treeData.value = [...newTreeData, ...treeData.value];

  if (jsonlFiles.length > 0) {
    await loadJsonlFile(jsonlFiles[0]);
  }
  if (!appStarted.value) { startApp(); }
};

const traverseFileTree = async (item: any): Promise<File[]> => {
  const files: File[] = [];
  const queue: any[] = [item];
  while (queue.length > 0) {
    const entry = queue.shift();
    if (entry.isFile) {
      const file = await new Promise<File>(resolve => entry.file(resolve));
      Object.defineProperty(file, 'webkitRelativePath', { value: entry.fullPath.substring(1) });
      files.push(file);
    } else if (entry.isDirectory) {
      const reader = entry.createReader();
      const entries = await new Promise<any[]>(resolve => reader.readEntries(resolve));
      queue.push(...entries);
    }
  }
  return files;
};

// --- 이벤트 핸들러 ---
const handleFileSelect = (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (input.files) processFiles(Array.from(input.files));
};

const handleFolderSelect = (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (input.files) processFiles(Array.from(input.files));
};

const handleDrop = async (event: DragEvent) => {
  event.preventDefault();
  isDraggingOver.value = false;
  isDraggingOverPanel.value = false;
  if (event.dataTransfer?.items) {
    const entry = event.dataTransfer.items[0].webkitGetAsEntry();
    const files = await traverseFileTree(entry);
    processFiles(files);
  }
};

const onFileItemClick = (item: TreeItem) => {
  if (item.type === 'folder') {
    item.isExpanded = !item.isExpanded;
  } else if (item.file) {
    loadJsonlFile(item.file);
    activeFileId.value = item.id;
  }
};

const removeItem = (itemToRemove: TreeItem) => {
  const wasActive = itemToRemove.id === activeFileId.value;
  const remove = (items: TreeItem[]): TreeItem[] => {
    return items.filter(item => {
      if (item.id === itemToRemove.id) {
        return false;
      }
      if (item.children) {
        item.children = remove(item.children);
      }
      return true;
    });
  };
  treeData.value = remove(treeData.value);

  if (treeData.value.length === 0) {
    appStarted.value = false;
    activeFileId.value = null;
  } else if (wasActive) {
    const firstFile = flattenedTree.value.find(item => item.type === 'file');
    if (firstFile && firstFile.file) {
      loadJsonlFile(firstFile.file);
      activeFileId.value = firstFile.id;
    } else {
      logs.value = [];
      activeFileId.value = null;
    }
  }
};

const flattenedTree = computed(() => {
  const flat: TreeItem[] = [];
  const traverse = (items: TreeItem[]) => {
    items.forEach(item => {
      flat.push(item);
      if (item.isExpanded && item.children) { traverse(item.children); }
    });
  };
  traverse(treeData.value);
  return flat;
});

import { ref, computed, nextTick, watch } from 'vue';

const processLogContent = computed(() => {
  return (content: string): LogPart[] => {
    const parts: LogPart[] = [];
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)\n```/g;
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(content)) !== null) {
      const [fullMatch, lang, code] = match;
      if (match.index > lastIndex) {
        parts.push({ type: 'text', content: content.substring(lastIndex, match.index) });
      }
      parts.push({ type: 'code', content: code, lang: lang || 'plaintext' });
      lastIndex = match.index + fullMatch.length;
    }

    if (lastIndex < content.length) {
      parts.push({ type: 'text', content: content.substring(lastIndex) });
    }
    return parts;
  };
});

const vHighlight: Directive<HTMLElement, { content: string; lang?: string }> = {
  mounted: (el, binding) => {
    el.innerHTML = binding.value.content;
    if (binding.value.lang) {
      el.className = `language-${binding.value.lang}`;
    }
    nextTick(() => {
      hljs.highlightElement(el);
    });
  },
  updated: (el, binding) => {
    el.innerHTML = binding.value.content;
    if (binding.value.lang) {
      el.className = `language-${binding.value.lang}`;
    }
    nextTick(() => {
      hljs.highlightElement(el);
    });
  },
};


</script>

<template>
  <!-- 1. 초기 시작 화면 -->
  <div v-if="!appStarted" 
       class="init-page-container"
       @dragover.prevent="isDraggingOver = true"
       @dragleave.prevent="isDraggingOver = false"
       @drop="handleDrop">
    <div class="init-content-wrapper">
      <h1 class="init-title">Log Viewer</h1>
      <p class="init-description">JSONL 형식의 로그 파일을 위한 간단한 뷰어입니다.</p>
      <div :class="['drop-zone', { 'is-dragging-over': isDraggingOver }]">
        <div class="drop-zone-content">
          <svg width="48" height="48" viewBox="0 0 16 16">
            <path fill="currentColor" d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
            <path fill="currentColor" d="M7.646 1.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 2.707V11.5a.5.5 0 0 1-1 0V2.707L5.354 4.854a.5.5 0 1 1-.708-.708l3-3z"/>
          </svg>
          <p>여기에 .jsonl 파일이나 폴더를 드래그 앤 드롭하세요.</p>
          <p class="or-text">또는</p>
          <div class="button-group">
            <button @click="fileInput?.click()" class="select-button">파일 선택</button>
            <button @click="folderInput?.click()" class="select-button">폴더 선택</button>
          </div>
        </div>
      </div>
      <input type="file" ref="fileInput" @change="handleFileSelect" style="display: none;" accept=".jsonl" />
      <input type="file" ref="folderInput" webkitdirectory directory multiple @change="handleFolderSelect" style="display: none;" />
    </div>
  </div>

  <div v-else class="app-layout">
    <div 
      class="file-panel"
      :class="{ 'is-dragging-over': isDraggingOverPanel }"
      @dragover.prevent="isDraggingOverPanel = true"
      @dragleave.prevent="isDraggingOverPanel = false"
      @drop="handleDrop">
      <ul class="file-list">
        <li v-for="item in flattenedTree" 
            :key="item.id" 
            class="file-item" 
            :class="{ 'active': item.id === activeFileId }" 
            :style="{ paddingLeft: `${item.depth * 20 + 16}px` }" 
            @click="onFileItemClick(item)">
          <span class="item-icon">
            <template v-if="item.type === 'folder'">{{ item.isExpanded ? '▼' : '▶' }}</template>
            <template v-else>📄</template>
          </span>
          <span class="item-name">{{ item.name }}</span>
          <span class="close-button" @click.stop="removeItem(item)">×</span>
        </li>
      </ul>
    </div>

    <div class="chat-panel">
      <div class="chat-container">
        <div v-if="error" class="message">
          <p class="error-message">{{ error }}</p>
        </div>
        <div v-else-if="logs.length === 0" class="message">
          <p class="loading-message">표시할 로그가 없습니다.</p>
        </div>
        <div v-else>
          <div v-for="(log, index) in logs" 
               :key="index" 
               :class="['message', `role-${log.role}`]">
            <div class="bubble">
              <div class="content">
                <template v-for="(part, pIndex) in processLogContent(log.content)" :key="pIndex">
                  <pre v-if="part.type === 'code'">
                    <code v-highlight="{ content: part.content, lang: part.lang }"></code>
                  </pre>
                  <p v-else v-html="part.content"></p>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="ghost-panel"></div>
  </div>
</template>

<style>
/* --- 초기 시작 화면 스타일 --- */
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

/* --- 메인 앱 레이아웃 --- */
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
.message.role-user + .message.role-assistant { margin-top: 0.75rem; }
.message.role-assistant + .message.role-user { margin-top: 2.5rem; }
.message { display: flex; }
.message.role-user { justify-content: flex-end; }
.message.role-assistant { justify-content: flex-start; }
.bubble { padding: 0.8rem 1.2rem; border-radius: 1.2rem; max-width: 85%; }
.message.role-user .bubble { background-color: #f0f0f0; }
.message.role-assistant .bubble { background-color: transparent; text-align: left; }
.content { white-space: pre-wrap; word-wrap: break-word; line-height: 1.6; }
.error-message, .loading-message { text-align: center; padding: 2rem; color: #888; }
.ghost-panel { width: 320px; flex-shrink: 0; }

/* highlight.js 스타일 */
pre code {
  display: block;
  overflow-x: auto;
  padding: 1em;
  background: #2d2d2d; /* 코드 블록 배경색 */
  color: #ccc; /* 코드 텍스트 색상 */
  border-radius: 8px;
}

.message.role-assistant .bubble pre code {
  background-color: #2d2d2d; /* 어시스턴트 버블 내 코드 블록 배경색 */
}

.message.role-user .bubble pre code {
  background-color: #3a3a3a; /* 사용자 버블 내 코드 블록 배경색 */
}

.content p {
  margin-bottom: 1em; /* 텍스트 단락 간 간격 */
}

.content p:last-child {
  margin-bottom: 0; /* 마지막 단락은 간격 없음 */
}

.content pre {
  margin-top: 1em;
  margin-bottom: 1em;
}

.content pre:first-child {
  margin-top: 0;
}

.content pre:last-child {
  margin-bottom: 0;
}
</style>
