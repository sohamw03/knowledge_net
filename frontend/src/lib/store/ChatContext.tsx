"use client";

import { ChatData, ChatState, Conversation, Message, ResearchOptions, ResearchResults, ResearchTree, StatusUpdate } from "@/lib/types";
import { ReactNode, createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { disconnectSocket, getSocket, initializeSocket } from "@/lib/socket";

// Utility functions for local storage
const saveToStorage = (data: ChatData) => {
  if (typeof window !== "undefined") {
    localStorage.setItem("chatData", JSON.stringify(data));
  }
};

const loadFromStorage = (): ChatData => {
  if (typeof window === "undefined") {
    return { conversations: [], currentConversationId: null };
  }
  const data = localStorage.getItem("chatData");
  if (!data) {
    return { conversations: [], currentConversationId: null };
  }
  try {
    const parsed = JSON.parse(data);
    return {
      conversations: Array.isArray(parsed.conversations)
        ? parsed.conversations.map((conv: Conversation) => ({
            ...conv,
            messages: Array.isArray(conv.messages)
              ? conv.messages.map((msg: Message) => ({
                  ...msg,
                  // Ensure media property is preserved if it exists
                  media: msg.media || undefined,
                }))
              : [],
          }))
        : [],
      currentConversationId: parsed.currentConversationId,
    };
  } catch (e) {
    return { conversations: [], currentConversationId: null };
  }
};

// Define the context type
interface ChatContextType {
  // State
  chatState: ChatState;
  conversations: Conversation[];
  currentConversationId: string | null;
  researchOptions: ResearchOptions;
  userInputRef: React.RefObject<HTMLTextAreaElement>;

  // Actions
  setResearchOptions: (options: ResearchOptions) => void;
  sendMessage: (content: string) => void;
  newConversation: () => void;
  selectConversation: (id: string) => void;
  deleteConversation: (id: string) => void;
  deleteAllConversations: () => void;
  abortResearch: () => void; // New function to abort research
}

// Create the context with a default value
const ChatContext = createContext<ChatContextType | undefined>(undefined);

// Provider component
export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const [chatState, setChatState] = useState<ChatState>({ messages: [], isLoading: false, error: null });
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [researchOptions, setResearchOptions] = useState<ResearchOptions>({
    depth: "basic",
    sources: true,
    citations: false,
    max_depth: 1,
    num_sites_per_query: 3,
  });

  const userInputRef = useRef<HTMLTextAreaElement>(null);

  // Focus management
  useEffect(() => {
    const focusInput = () => {
      setTimeout(() => {
        userInputRef.current?.focus();
      }, 100);
    };

    focusInput();
  }, [currentConversationId]);

  // Load initial data
  useEffect(() => {
    const data = loadFromStorage();
    setConversations(data.conversations);
    setCurrentConversationId(data.currentConversationId);

    if (data.currentConversationId) {
      const conversation = data.conversations.find((c) => c.id === data.currentConversationId);
      if (conversation) {
        // Check if any loaded message has isProgress true
        let messages = conversation.messages;
        if (messages.some((msg) => msg.isProgress === true)) {
          // Convert any progress messages to error messages
          messages = messages.map((msg) => (msg.isProgress === true ? { ...msg, content: "Connection error", isProgress: false } : msg));
        }

        setChatState((prev) => ({ ...prev, messages, isLoading: false }));
      }
    }
  }, []);

  // Socket initialization
  useEffect(() => {
    const socket = initializeSocket();

    socket.on("connect", () => {
      console.log("Connected to research server");
    });

    socket.on("disconnect", () => {
      console.log("Disconnected from research server");

      // When socket disconnects, update any progress messages to show connection error
      setChatState((prevState) => {
        const updatedMessages = prevState.messages.map((msg) => (msg.isProgress === true ? { ...msg, content: "Connection error", isProgress: false } : msg));

        return {
          ...prevState,
          messages: updatedMessages,
          isLoading: false,
          error: "Lost connection to research server",
        };
      });
    });

    socket.on("status", (data: StatusUpdate) => {
      setChatState((prevState) => {
        const messages = [...prevState.messages];
        const progressText = data.message;
        const progress = data.progress;

        // Find the last assistant message that is a progress update
        const lastProgressIndex = messages.findLastIndex((msg) => msg.role === "assistant" && msg.isProgress === true);

        if (lastProgressIndex !== -1) {
          // Update existing progress message with research_tree data
          messages[lastProgressIndex] = {
            ...messages[lastProgressIndex],
            content: progressText,
            progress: progress,
            timestamp: new Date(),
            research_tree: data.research_tree, // Update the research_tree in real-time
          };
        } else {
          // Add new progress message with research_tree
          messages.push({
            id: uuidv4(),
            content: progressText,
            role: "assistant",
            timestamp: new Date(),
            progress: progress,
            isProgress: true,
            research_tree: data.research_tree, // Include the research_tree
            media: {}, // Initialize empty media object
          });
        }

        return {
          ...prevState,
          messages,
          isLoading: true,
        };
      });
    });

    socket.on("research_complete", (results: ResearchResults) => {
      setChatState((prevState) => {
        const messages = [...prevState.messages];

        // Remove the last progress message if it exists
        const lastProgressIndex = messages.findLastIndex((msg) => msg.role === "assistant" && msg.isProgress === true);

        if (lastProgressIndex !== -1) {
          messages.splice(lastProgressIndex, 1);
        }

        const newMessages = [
          ...messages,
          {
            id: uuidv4(),
            content: results.content || "Error: No content available",
            role: "assistant" as const,
            timestamp: new Date(results.timestamp),
            media: results.media,
            research_tree: results.research_tree,
          },
        ];

        // Save updated messages to localStorage
        const updatedState = {
          ...prevState,
          isLoading: false,
          messages: newMessages,
        };

        // Update localStorage with the new messages
        const updatedData: ChatData = {
          conversations: conversations.map((conv) => ({
            ...conv,
            messages: conv.id === currentConversationId ? newMessages : conv.messages || [],
            lastUpdated: conv.id === currentConversationId ? new Date().toISOString() : conv.lastUpdated,
          })),
          currentConversationId,
        };

        saveToStorage(updatedData);

        return updatedState;
      });
    });

    socket.on("research_aborted", () => {
      setChatState((prevState) => {
        const messages = [...prevState.messages];
        const lastProgressIndex = messages.findLastIndex((msg) => msg.role === "assistant" && msg.isProgress === true);

        if (lastProgressIndex !== -1) {
          messages.splice(lastProgressIndex, 1);
        }

        // Add a message indicating the research was canceled
        messages.push({
          id: uuidv4(),
          content: "Research has been canceled.",
          role: "assistant",
          timestamp: new Date(),
        });

        return {
          ...prevState,
          isLoading: false,
          messages,
        };
      });
    });

    socket.on("error", (error: { message: string }) => {
      setChatState((prevState) => ({
        ...prevState,
        error: error.message,
        isLoading: false,
      }));
    });

    return () => {
      disconnectSocket();
    };
  }, []);

  // Save data whenever conversations or messages change
  useEffect(() => {
    const data: ChatData = {
      conversations: conversations.map((conv) => ({
        ...conv,
        messages: conv.id === currentConversationId ? chatState.messages : conv.messages || [],
      })),
      currentConversationId,
    };

    saveToStorage(data);
  }, [conversations, currentConversationId, chatState.messages]);

  // Action handlers
  const sendMessage = useCallback(
    (content: string) => {
      if (!content.trim()) return;

      let conversationId = currentConversationId;
      const newMessage: Message = {
        id: uuidv4(),
        content,
        role: "user",
        timestamp: new Date(),
      };
      const newLoadingMessage: Message = {
        id: uuidv4(),
        content: "Loading...",
        role: "assistant",
        timestamp: new Date(),
        isProgress: true,
      };

      // Create a new conversation if none exists
      if (!conversationId) {
        conversationId = uuidv4();
        setCurrentConversationId(conversationId);
        setConversations((prev) => [
          {
            id: conversationId as string,
            title: content.length > 30 ? `${content.substring(0, 30)}...` : content,
            lastUpdated: new Date().toISOString(),
            messages: [newMessage],
            active: true,
          },
          ...prev.map((c) => ({ ...c, active: false })),
        ]);
      } else {
        // Update the existing conversation
        setConversations((prev) =>
          prev.map((conv) => ({
            ...conv,
            lastUpdated: conv.id === conversationId ? new Date().toISOString() : conv.lastUpdated,
            active: conv.id === conversationId,
            messages: conv.id === conversationId ? [...(conv.messages || []), newMessage] : conv.messages || [],
          }))
        );
      }

      setChatState((prevState) => ({
        ...prevState,
        messages: [...prevState.messages, newMessage, newLoadingMessage],
        isLoading: true,
        error: null,
      }));

      // Send message to server via socket
      try {
        const socket = getSocket();
        socket.emit("start_research", {
          topic: content,
          max_depth: researchOptions.max_depth,
          num_sites_per_query: researchOptions.num_sites_per_query,
        });
      } catch (error) {
        setChatState((prevState) => ({
          ...prevState,
          error: "Failed to connect to research server",
          isLoading: false,
        }));
      }
    },
    [currentConversationId, conversations, researchOptions]
  );

  const newConversation = useCallback(() => {
    userInputRef.current?.focus();
    setCurrentConversationId(null);
    setChatState(() => ({
      messages: [],
      isLoading: false,
      error: null,
    }));
  }, []);

  const selectConversation = useCallback((id: string) => {
    const data = loadFromStorage();
    const conversation = data.conversations.find((c) => c.id === id);

    setCurrentConversationId(id);
    setChatState((prev) => ({
      ...prev,
      messages: conversation?.messages || [],
      isLoading: false,
      error: null,
    }));
    setConversations((prev) =>
      prev.map((conv) => ({
        ...conv,
        active: conv.id === id,
      }))
    );
  }, []);

  const deleteConversation = useCallback(
    (id: string) => {
      setConversations((prev) => prev.filter((conv) => conv.id !== id));
      if (currentConversationId === id) {
        newConversation();
      }
    },
    [currentConversationId, newConversation]
  );

  const deleteAllConversations = useCallback(() => {
    setConversations([]);
    newConversation();
  }, [newConversation]);

  const abortResearch = useCallback(() => {
    try {
      const socket = getSocket();
      socket.emit("abort_research");

      setChatState((prevState) => ({
        ...prevState,
        isLoading: true,
      }));
    } catch (error) {
      console.error("Failed to abort research:", error);
      setChatState((prevState) => ({
        ...prevState,
        error: "Failed to abort research",
      }));
    }
  }, []);

  // Keyboard shortcuts | Ctrl + I to new chat
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.key === "i") {
        event.preventDefault();
        newConversation();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  const value = {
    chatState,
    conversations,
    currentConversationId,
    researchOptions,
    userInputRef,
    setResearchOptions,
    sendMessage,
    newConversation,
    selectConversation,
    deleteConversation,
    deleteAllConversations,
    abortResearch,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};

// Custom hook for using the chat context
export const useChatContext = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error("useChatContext must be used within a ChatProvider");
  }
  return context;
};
