export interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
  media?: {
    links?: Array<{ text: string; url: string }>;
    images?: string[];
  };
  research_tree?: ResearchTree;
  progress?: number;
  isProgress?: boolean;
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
  max_depth: number;
  num_sites_per_query: number;
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

// Simplified research results based on actual server output
export interface ResearchResults {
  topic: string;
  timestamp: string;
  // Optional fields not present in basic server response
  content?: string;
  media?: {
    images?: string[];
    videos?: string[];
    links?: Array<{
      text: string;
      url: string;
    }>;
  };
  research_tree?: ResearchTree;
}

export interface ResearchTree {
  query: string;
  depth: number;
  sources: string[];
  children: ResearchTree[];
}

export interface ConversationListProps {
  conversations: Conversation[];
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onDeleteAllConversations: () => void;
}
