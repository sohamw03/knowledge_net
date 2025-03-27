"use client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { disconnectSocket, getSocket, initializeSocket } from "@/lib/socket";
import { ChatData, ChatState, Conversation, Message, ResearchOptions, ResearchResults, StatusUpdate } from "@/lib/types";
import { useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import ChatHistory from "./ChatHistory";
import MessageInput from "./MessageInput";
import ResearchControls from "./ResearchControls";
import ChatLayout from "./ui/ChatLayout";
import ConversationList from "./ui/ConversationList";

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
      conversations: Array.isArray(parsed.conversations) ? parsed.conversations : [],
      currentConversationId: parsed.currentConversationId,
    };
  } catch (e) {
    return { conversations: [], currentConversationId: null };
  }
};

const ChatInterface = () => {
  const [chatState, setChatState] = useState<ChatState>({ messages: [], isLoading: false, error: null });
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);

  const [researchOptions, setResearchOptions] = useState<ResearchOptions>({
    depth: "basic",
    sources: true,
    citations: false,
    max_depth: 1,
    max_breadth: 3,
    num_sites_per_query: 5,
  });

  const userInputRef = useRef<HTMLTextAreaElement>(null);

  // Add this effect for focus management
  useEffect(() => {
    const focusInput = () => {
      setTimeout(() => {
        userInputRef.current?.focus();
      }, 100);
    };

    focusInput();
  }, [currentConversationId]);

  // Initialize socket once
  useEffect(() => {
    const socket = initializeSocket();

    socket.on("connect", () => {
      console.log("Connected to research server");
    });

    socket.on("disconnect", () => {
      console.log("Disconnected from research server");
    });

    socket.on("status", (data: StatusUpdate) => {
      setChatState((prevState) => {
        const messages = [...prevState.messages];
        const progressText = `(${data.progress}%) ${data.message}`;

        // Find the last assistant message that is a progress update
        const lastProgressIndex = messages.findLastIndex((msg) => msg.role === "assistant" && msg.content.includes("%)"));

        if (lastProgressIndex !== -1) {
          // Update existing progress message
          messages[lastProgressIndex] = {
            ...messages[lastProgressIndex],
            content: progressText,
          };
        } else {
          // Add new progress message
          messages.push({
            id: uuidv4(),
            content: progressText,
            role: "assistant",
            timestamp: new Date(),
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
        const lastProgressIndex = messages.findLastIndex((msg) => msg.role === "assistant" && msg.content.includes("%)"));
        if (lastProgressIndex !== -1) {
          messages.splice(lastProgressIndex, 1);
        }

        // Format research stats and response
        const stats = [`Total Queries: ${results.metadata.total_queries}`, `Sources Used: ${results.metadata.total_sources}`, `Search Depth: ${results.metadata.max_depth_reached}`].join(" | ");

        const formattedResponse = [results.content, `\n\n---\n**Research Stats:**\n${stats}`, results.media?.images?.length ? `\n\n**Relevant Images:**\n${results.media.images.join("\n")}` : ""].join("");

        const newMessages = [
          ...messages,
          {
            id: uuidv4(),
            content: formattedResponse,
            role: "assistant" as const,
            timestamp: new Date(results.timestamp),
          },
        ];

        return {
          ...prevState,
          isLoading: false,
          messages: newMessages,
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
  }, []); // Empty dependency array

  // Load initial data
  useEffect(() => {
    const data = loadFromStorage();
    setConversations(data.conversations);
    setCurrentConversationId(data.currentConversationId);

    if (data.currentConversationId) {
      const currentConv = data.conversations.find((c) => c.id === data.currentConversationId);
      if (currentConv) {
        setChatState((prev) => ({ ...prev, messages: currentConv.messages }));
      }
    }
  }, []);

  useEffect(() => {
    const currentConv = conversations.find((c) => c.id === currentConversationId);

    const data: ChatData = {
      conversations: conversations.map((conv) => ({
        ...conv,
        messages: conv.id === currentConversationId ? chatState.messages : conv.messages || [],
      })),
      currentConversationId,
    };

    saveToStorage(data);
  }, [conversations, currentConversationId, chatState.messages]);

  const handleSendMessage = (content: string) => {
    if (!content.trim()) return;

    let conversationId = currentConversationId;
    const newMessage: Message = {
      id: uuidv4(),
      content,
      role: "user",
      timestamp: new Date(),
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
      messages: [...prevState.messages, newMessage],
      isLoading: true,
      error: null,
    }));

    // Send message to server via socket
    try {
      const socket = getSocket();
      socket.emit("start_research", {
        topic: content,
        max_depth: researchOptions.max_depth,
        max_breadth: researchOptions.max_breadth,
        num_sites_per_query: researchOptions.num_sites_per_query,
      });
    } catch (error) {
      setChatState((prevState) => ({
        ...prevState,
        error: "Failed to connect to research server",
        isLoading: false,
      }));
    }
  };

  const handleNewConversation = () => {
    userInputRef.current?.focus();
    setCurrentConversationId(null);
    setChatState((prev) => ({
      messages: [],
      isLoading: false,
      error: null,
    }));
  };

  const handleSelectConversation = (id: string) => {
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
  };

  const handleDeleteConversation = (id: string) => {
    setConversations((prev) => prev.filter((conv) => conv.id !== id));
    if (currentConversationId === id) {
      handleNewConversation();
    }
  };

  const handleDeleteAllConversations = () => {
    setConversations([]);
    handleNewConversation();
  };

  const sidebar = <ConversationList conversations={conversations} onNewConversation={handleNewConversation} onSelectConversation={handleSelectConversation} onDeleteConversation={handleDeleteConversation} onDeleteAllConversations={handleDeleteAllConversations} />;

  const mainContent = (
    <div className="flex flex-col w-full h-full relative" tabIndex={-1}>
      <ChatHistory messages={chatState.messages} isLoading={chatState.isLoading} />

      {chatState.error && (
        <Alert variant="destructive" className="mx-2 my-2 mb-28 w-90 bg-red-950 text-red-50">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{chatState.error}</AlertDescription>
        </Alert>
      )}

      <MessageInput onSendMessage={handleSendMessage} isLoading={chatState.isLoading} userInputRef={userInputRef} />
    </div>
  );

  return <ChatLayout sidebar={sidebar} mainContent={mainContent} settingsPanel={<ResearchControls options={researchOptions} onOptionChange={setResearchOptions} />} />;
};

export default ChatInterface;
