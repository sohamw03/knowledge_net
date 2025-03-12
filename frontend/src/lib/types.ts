export interface Message {
  id: string;
  content: string;
  role: "user" | "assistant" | "system";
  timestamp: Date;
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
}

export interface ResearchOptions {
  depth: "basic" | "intermediate" | "deep";
  sources: boolean;
  citations: boolean;
}

export interface ChatData {
  conversations: Conversation[];
  currentConversationId: string | null;
}

export interface Conversation {
  id: string;
  title: string;
  lastUpdated: string;
  messages: Message[];
  active: boolean;
}

export interface StatusUpdate {
  message: string;
  progress: number;
}

export interface ResearchNode {
  query: string;
  children?: ResearchNode[];
}

export interface ResearchMetadata {
  total_queries: number;
  total_sources: number;
  max_depth_reached: number;
  total_tokens: number;
}

export interface ResearchResults {
  topic: string;
  timestamp: string;
  content: string;
  media?: {
    images?: string[];
    videos?: string[];
  };
  research_tree: ResearchNode;
  metadata: ResearchMetadata;
}
