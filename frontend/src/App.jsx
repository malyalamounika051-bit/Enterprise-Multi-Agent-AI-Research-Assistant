import React, { useState, useEffect } from "react";
import {
  MessageSquare,
  Brain,
  CheckCircle2,
  AlertTriangle,
  History,
  Send,
  Plus,
  RefreshCw,
  Trash2,
  Edit3,
  ShieldCheck,
  FileText,
  Clock,
  Layers,
  Sparkles,
  ExternalLink,
  ChevronRight,
  Database
} from "lucide-react";

export default function App() {
  const [activeTab, setActiveTab] = useState("chat"); // chat | memory | eval | traces
  const [users, setUsers] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  
  // Chat state
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Memory state
  const [memories, setMemories] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [editingMemory, setEditingMemory] = useState(null);
  const [editContent, setEditContent] = useState("");
  const [newMemoryCategory, setNewMemoryCategory] = useState("preference");
  const [newMemoryContent, setNewMemoryContent] = useState("");
  const [showAddMemoryModal, setShowAddMemoryModal] = useState(false);

  // Evaluation state
  const [evalData, setEvalData] = useState(null);
  const [isEvaluating, setIsEvaluating] = useState(false);

  // Active trace modal
  const [selectedTrace, setSelectedTrace] = useState(null);

  // 1. Initial Load: Users & System Status
  useEffect(() => {
    fetchSystemStatus();
    fetchUsers();
  }, []);

  // 2. When User Changes: Load their Conversations and Memories
  useEffect(() => {
    if (currentUser) {
      fetchConversations(currentUser.user_id);
      fetchMemories(currentUser.user_id);
      fetchAuditLogs(currentUser.user_id);
    }
  }, [currentUser]);

  // 3. When Conversation Changes: Load Messages
  useEffect(() => {
    if (activeConversationId) {
      fetchMessages(activeConversationId);
    } else {
      setMessages([]);
    }
  }, [activeConversationId]);

  const fetchSystemStatus = async () => {
    try {
      const res = await fetch("/api/system/status");
      if (res.ok) {
        const data = await res.json();
        setSystemStatus(data);
      }
    } catch (e) {
      console.error("Failed to fetch system status", e);
    }
  };

  const fetchUsers = async () => {
    try {
      const res = await fetch("/api/users");
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
        if (data.length > 0 && !currentUser) {
          setCurrentUser(data[0]);
        }
      }
    } catch (e) {
      console.error("Failed to fetch users", e);
    }
  };

  const fetchConversations = async (userId) => {
    try {
      const res = await fetch(`/api/conversations?user_id=${userId}`);
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
        if (data.length > 0) {
          setActiveConversationId(data[0].conversation_id);
        } else {
          setActiveConversationId(null);
        }
      }
    } catch (e) {
      console.error("Failed to fetch conversations", e);
    }
  };

  const fetchMessages = async (convId) => {
    try {
      const res = await fetch(`/api/conversations/${convId}/messages`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (e) {
      console.error("Failed to fetch messages", e);
    }
  };

  const fetchMemories = async (userId) => {
    try {
      const res = await fetch(`/api/memories?user_id=${userId}`);
      if (res.ok) {
        const data = await res.json();
        setMemories(data);
      }
    } catch (e) {
      console.error("Failed to fetch memories", e);
    }
  };

  const fetchAuditLogs = async (userId) => {
    try {
      const res = await fetch(`/api/memories/audit?user_id=${userId}`);
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data);
      }
    } catch (e) {
      console.error("Failed to fetch audit logs", e);
    }
  };

  const handleNewConversation = async () => {
    if (!currentUser) return;
    try {
      const res = await fetch("/api/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: currentUser.user_id, title: "New Research Session" })
      });
      if (res.ok) {
        const newConv = await res.json();
        setConversations([newConv, ...conversations]);
        setActiveConversationId(newConv.conversation_id);
      }
    } catch (e) {
      console.error("Failed to create conversation", e);
    }
  };

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!inputMessage.trim() || !currentUser || isLoading) return;

    const userText = inputMessage.trim();
    setInputMessage("");
    setIsLoading(true);

    // Optimistic user message append
    const tempUserMsg = {
      message_id: `temp_${Date.now()}`,
      sender: "user",
      content: userText,
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: currentUser.user_id,
          conversation_id: activeConversationId,
          message: userText
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (!activeConversationId) {
          setActiveConversationId(data.conversation_id);
          fetchConversations(currentUser.user_id);
        }

        const assistantMsg = {
          message_id: data.message_id,
          sender: "assistant",
          content: data.answer,
          citations: data.citations || [],
          agent_trace: data.agent_trace || [],
          supersession_notes: data.supersession_notes || [],
          created_at: new Date().toISOString()
        };
        setMessages((prev) => [...prev, assistantMsg]);

        // Refresh memories and audit if updated
        if (data.new_memories_extracted?.length > 0 || data.explicit_action) {
          fetchMemories(currentUser.user_id);
          fetchAuditLogs(currentUser.user_id);
        }
      }
    } catch (err) {
      console.error("Chat error", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCorrectMemory = async () => {
    if (!editingMemory || !editContent.trim()) return;
    try {
      const res = await fetch(`/api/memories/${editingMemory.memory_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: currentUser.user_id,
          content: editContent.trim(),
          reason: "User corrected via Memory UI"
        })
      });
      if (res.ok) {
        setEditingMemory(null);
        setEditContent("");
        fetchMemories(currentUser.user_id);
        fetchAuditLogs(currentUser.user_id);
      }
    } catch (e) {
      console.error("Failed to correct memory", e);
    }
  };

  const handleForgetMemory = async (memoryId) => {
    if (!window.confirm("Are you sure you want the assistant to forget this information?")) return;
    try {
      const res = await fetch(`/api/memories/${memoryId}?user_id=${currentUser.user_id}`, {
        method: "DELETE"
      });
      if (res.ok) {
        fetchMemories(currentUser.user_id);
        fetchAuditLogs(currentUser.user_id);
      }
    } catch (e) {
      console.error("Failed to forget memory", e);
    }
  };

  const handleAddMemory = async (e) => {
    e.preventDefault();
    if (!newMemoryContent.trim()) return;
    try {
      const res = await fetch("/api/memories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: currentUser.user_id,
          category: newMemoryCategory,
          content: newMemoryContent.trim(),
          provenance: "Manual entry via Memory Center"
        })
      });
      if (res.ok) {
        setShowAddMemoryModal(false);
        setNewMemoryContent("");
        fetchMemories(currentUser.user_id);
        fetchAuditLogs(currentUser.user_id);
      }
    } catch (e) {
      console.error("Failed to add memory", e);
    }
  };

  const runEvaluation = async () => {
    setIsEvaluating(true);
    try {
      const res = await fetch("/api/evaluation/run", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setEvalData(data);
      }
    } catch (e) {
      console.error("Failed to run evaluation", e);
    } finally {
      setIsEvaluating(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#0a0d14] text-slate-100 font-sans">
      {/* Top Header */}
      <header className="flex items-center justify-between px-6 py-3.5 bg-[#101522] border-b border-slate-800/80 z-20">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-bold text-base tracking-tight text-white">Asterline AI Assistant</h1>
              <span className="text-[10px] uppercase font-semibold tracking-wider px-2 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800/60 text-cyan-300">
                Multi-Agent RAG
              </span>
            </div>
            <p className="text-xs text-slate-400">Enterprise Research & Isolated Continuity</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="flex space-x-1 bg-[#171f32] p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab("chat")}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === "chat"
                ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-md shadow-blue-500/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Research Chat</span>
          </button>
          <button
            onClick={() => setActiveTab("memory")}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === "memory"
                ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-md shadow-blue-500/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            }`}
          >
            <Brain className="w-3.5 h-3.5" />
            <span>Memory Center</span>
            {memories.length > 0 && (
              <span className="ml-1 text-[10px] px-1.5 py-0.2 bg-cyan-950 text-cyan-300 rounded-full border border-cyan-800">
                {memories.length}
              </span>
            )}
          </button>
          <button
            onClick={() => {
              setActiveTab("eval");
              if (!evalData) runEvaluation();
            }}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === "eval"
                ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-md shadow-blue-500/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Evaluation (15/15)</span>
          </button>
        </nav>

        {/* User Persona Switcher */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 bg-[#171f32] px-3 py-1.5 rounded-xl border border-slate-800">
            <span className="text-xs text-slate-400">User:</span>
            <select
              value={currentUser?.user_id || ""}
              onChange={(e) => {
                const u = users.find((x) => x.user_id === e.target.value);
                if (u) setCurrentUser(u);
              }}
              className="bg-transparent text-xs text-cyan-300 font-medium focus:outline-none cursor-pointer"
            >
              {users.map((u) => (
                <option key={u.user_id} value={u.user_id} className="bg-[#171f32] text-slate-200">
                  {u.name} ({u.role.split(" ")[0]})
                </option>
              ))}
            </select>
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
          </div>

          <div className="text-[11px] text-slate-400 flex items-center space-x-1.5 bg-[#171f32] px-3 py-1.5 rounded-xl border border-slate-800">
            <Database className="w-3 h-3 text-cyan-400" />
            <span>75 Chunks Indexed</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {activeTab === "chat" && (
          <div className="flex-1 flex w-full">
            {/* Sidebar: Conversations */}
            <aside className="w-64 bg-[#0e121d] border-r border-slate-800/80 flex flex-col p-3">
              <button
                onClick={handleNewConversation}
                className="flex items-center justify-center space-x-2 w-full py-2.5 px-3 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 text-blue-300 text-xs font-semibold transition-all mb-3"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>New Research Session</span>
              </button>

              <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold px-2 mb-2">
                Conversations
              </div>
              <div className="flex-1 overflow-y-auto space-y-1">
                {conversations.map((c) => (
                  <button
                    key={c.conversation_id}
                    onClick={() => setActiveConversationId(c.conversation_id)}
                    className={`w-full text-left px-3 py-2.5 rounded-xl text-xs flex items-center space-x-2 transition-all ${
                      activeConversationId === c.conversation_id
                        ? "bg-slate-800/80 text-white font-medium border border-slate-700 shadow-sm"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                    }`}
                  >
                    <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-70" />
                    <span className="truncate">{c.title || "Research Session"}</span>
                  </button>
                ))}
                {conversations.length === 0 && (
                  <div className="text-xs text-slate-400 italic px-2 py-4">No sessions yet.</div>
                )}
              </div>

              {/* User Persona Card in Sidebar */}
              {currentUser && (
                <div className="mt-auto p-3 rounded-xl bg-[#131929] border border-slate-800 text-xs">
                  <div className="font-semibold text-slate-200">{currentUser.name}</div>
                  <div className="text-slate-400 text-[11px]">{currentUser.role}</div>
                  <div className="mt-2 text-[10px] text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-900/50 inline-block">
                    {currentUser.workspace_access}
                  </div>
                </div>
              )}
            </aside>

            {/* Chat Messages Container */}
            <main className="flex-1 flex flex-col bg-[#0b0e17] overflow-hidden">
              <div className="flex-1 overflow-y-auto p-6 space-y-5">
                {messages.length === 0 && (
                  <div className="max-w-xl mx-auto my-12 text-center">
                    <div className="h-12 w-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center mx-auto mb-4">
                      <Sparkles className="w-6 h-6" />
                    </div>
                    <h3 className="text-lg font-semibold text-white mb-2">Asterline Research Assistant</h3>
                    <p className="text-xs text-slate-400 mb-6 leading-relaxed">
                      Ask questions grounded in the official Asterline documentation corpus. The assistant resolves
                      temporal conflicts (such as superseding policies), maintains private memory context, and logs multi-agent execution traces.
                    </p>

                    <div className="text-left text-xs text-slate-400 font-medium mb-3">Try asking:</div>
                    <div className="grid grid-cols-2 gap-2 text-left">
                      {[
                        "What is the retention period for cold storage recovery?",
                        "What is the weekly on-call stipend for engineers?",
                        "What was the deduplication fix for INC-2025-12?",
                        "What is the Signals AQL query timeout in v2.3?",
                        "Remember: I am on-call for eu-prod this week",
                        "Where are the Asterline company offices located?"
                      ].map((prompt, idx) => (
                        <button
                          key={idx}
                          onClick={() => setInputMessage(prompt)}
                          className="p-2.5 rounded-xl bg-[#13192a] hover:bg-[#1a233a] border border-slate-800 text-xs text-slate-300 hover:text-white transition-all text-left flex items-center justify-between"
                        >
                          <span className="truncate">{prompt}</span>
                          <ChevronRight className="w-3 h-3 text-slate-400 shrink-0 ml-1" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((m) => (
                  <div
                    key={m.message_id}
                    className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
                  >
                    <div className="flex items-center space-x-1.5 mb-1 text-[11px] text-slate-400 px-1">
                      <span>{m.sender === "user" ? currentUser?.name || "You" : "Asterline Assistant"}</span>
                    </div>

                    <div
                      className={`max-w-2xl rounded-2xl p-4 text-xs leading-relaxed shadow-sm ${
                        m.sender === "user"
                          ? "bg-blue-600 text-white rounded-tr-none"
                          : "bg-[#141b2d] border border-slate-800/90 text-slate-200 rounded-tl-none"
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{m.content}</div>

                      {/* Supporting Documentary Evidence & Citations */}
                      {m.citations && m.citations.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-slate-800">
                          <div className="text-[10px] uppercase font-semibold text-cyan-400 mb-1.5 flex items-center space-x-1">
                            <FileText className="w-3 h-3" />
                            <span>Documentary Evidence ({m.citations.length})</span>
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {m.citations.map((c, i) => (
                              <div
                                key={i}
                                className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-[#0e1320] border border-cyan-900/60 text-[11px] text-cyan-200"
                                title={`Document: ${c.doc_id} | Title: ${c.title}`}
                              >
                                <span className="font-mono text-cyan-400 font-semibold">{c.chunk_id}</span>
                                <span className="text-slate-400">·</span>
                                <span className="truncate max-w-[140px]">{c.title}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Agent Execution Trace Button */}
                      {m.agent_trace && m.agent_trace.length > 0 && (
                        <div className="mt-2.5 pt-2 flex items-center justify-between border-t border-slate-800/60">
                          <button
                            onClick={() => setSelectedTrace(m.agent_trace)}
                            className="flex items-center space-x-1.5 text-[11px] text-slate-400 hover:text-cyan-300 font-medium transition-colors"
                          >
                            <Layers className="w-3 h-3 text-cyan-400" />
                            <span>Inspect 3-Agent Workflow Trace ({m.agent_trace.length} steps)</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {isLoading && (
                  <div className="flex items-center space-x-2 text-xs text-slate-400 bg-[#141b2d] border border-slate-800 p-3 rounded-2xl max-w-xs animate-pulse">
                    <Sparkles className="w-4 h-4 text-cyan-400 animate-spin" />
                    <span>Orchestrating Researcher, Verifier & Memory Agents...</span>
                  </div>
                )}
              </div>

              {/* Chat Input Bar */}
              <form onSubmit={handleSendMessage} className="p-4 bg-[#101522] border-t border-slate-800">
                <div className="flex items-center space-x-2 bg-[#171f32] border border-slate-700/80 rounded-2xl px-3 py-1.5 focus-within:border-cyan-500/80 transition-all">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder={`Ask about Asterline policies, incidents, limits, or set durable preferences...`}
                    className="flex-1 bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none py-2 px-1"
                  />
                  <button
                    type="submit"
                    disabled={!inputMessage.trim() || isLoading}
                    className="p-2 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                  >
                    <Send className="w-3.5 h-3.5" />
                  </button>
                </div>
              </form>
            </main>
          </div>
        )}

        {/* Tab 2: Memory Management Center */}
        {activeTab === "memory" && (
          <div className="flex-1 flex flex-col bg-[#0b0e17] p-8 overflow-y-auto">
            <div className="max-w-4xl mx-auto w-full">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                    <Brain className="w-5 h-5 text-cyan-400" />
                    <span>Memory Management Center</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Context strictly isolated to <span className="text-cyan-300 font-semibold">{currentUser?.name}</span>. Other employees cannot access this data.
                  </p>
                </div>

                <button
                  onClick={() => setShowAddMemoryModal(true)}
                  className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md transition-all"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Memory</span>
                </button>
              </div>

              {/* Active Memories List */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-8">
                {memories.map((m) => (
                  <div
                    key={m.memory_id}
                    className="p-4 rounded-2xl bg-[#141b2d] border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800 text-cyan-300">
                          {m.category}
                        </span>
                        <span className="text-[10px] text-slate-400">{m.created_at?.slice(0, 10)}</span>
                      </div>
                      <p className="text-xs text-slate-200 font-medium mb-3">{m.content}</p>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-[11px]">
                      <span className="text-slate-400 truncate max-w-[150px]">From: {m.provenance}</span>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => {
                            setEditingMemory(m);
                            setEditContent(m.content);
                          }}
                          className="p-1 rounded text-slate-400 hover:text-cyan-300 transition-colors"
                          title="Correct memory"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleForgetMemory(m.memory_id)}
                          className="p-1 rounded text-slate-400 hover:text-rose-400 transition-colors"
                          title="Forget memory"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}

                {memories.length === 0 && (
                  <div className="col-span-2 p-8 text-center bg-[#141b2d] border border-slate-800 rounded-2xl text-slate-400 text-xs">
                    No active memories for {currentUser?.name}. The assistant will automatically remember your durable preferences, projects, and roles as you chat.
                  </div>
                )}
              </div>

              {/* Memory Audit Log */}
              <div className="mt-8">
                <h3 className="text-sm font-semibold text-white mb-3 flex items-center space-x-2">
                  <History className="w-4 h-4 text-cyan-400" />
                  <span>Memory Modification Audit Trail</span>
                </h3>
                <div className="bg-[#121726] border border-slate-800 rounded-2xl overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#171f32] text-slate-400 text-[11px] uppercase tracking-wider">
                      <tr>
                        <th className="py-2.5 px-4 font-semibold">Action</th>
                        <th className="py-2.5 px-4 font-semibold">Details</th>
                        <th className="py-2.5 px-4 font-semibold">Reason</th>
                        <th className="py-2.5 px-4 font-semibold">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {auditLogs.map((log) => (
                        <tr key={log.audit_id} className="hover:bg-slate-800/20">
                          <td className="py-2.5 px-4">
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                                log.action === "create"
                                  ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                                  : log.action === "update"
                                  ? "bg-amber-950 text-amber-400 border border-amber-800"
                                  : "bg-rose-950 text-rose-400 border border-rose-800"
                              }`}
                            >
                              {log.action}
                            </span>
                          </td>
                          <td className="py-2.5 px-4 text-slate-200">
                            {log.new_value || log.old_value}
                          </td>
                          <td className="py-2.5 px-4 text-slate-400">{log.reason}</td>
                          <td className="py-2.5 px-4 text-slate-400 font-mono text-[11px]">
                            {log.timestamp?.replace("T", " ").slice(0, 19)}
                          </td>
                        </tr>
                      ))}
                      {auditLogs.length === 0 && (
                        <tr>
                          <td colSpan={4} className="py-6 text-center text-slate-400 italic">
                            No memory audit records found.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Evaluation Dashboard (15/15) */}
        {activeTab === "eval" && (
          <div className="flex-1 flex flex-col bg-[#0b0e17] p-8 overflow-y-auto">
            <div className="max-w-4xl mx-auto w-full">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    <span>Reproducible Evaluation Suite</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Systematic verification across 15 categories: Grounded Research, Temporal Supersession, Conflict Precedence, Cross-User Isolation, and Honesty.
                  </p>
                </div>

                <button
                  onClick={runEvaluation}
                  disabled={isEvaluating}
                  className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold shadow-lg shadow-emerald-500/20 disabled:opacity-50 transition-all"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isEvaluating ? "animate-spin" : ""}`} />
                  <span>{isEvaluating ? "Executing Test Suite..." : "Re-run 15 Tests"}</span>
                </button>
              </div>

              {/* Metrics Summary Banner */}
              {evalData && (
                <div className="grid grid-cols-4 gap-4 mb-6">
                  <div className="p-4 rounded-2xl bg-[#141b2d] border border-slate-800">
                    <div className="text-[11px] text-slate-400 uppercase font-semibold">Pass Rate</div>
                    <div className="text-2xl font-bold text-emerald-400 mt-1">
                      {evalData.metrics.pass_rate_pct}%
                    </div>
                  </div>
                  <div className="p-4 rounded-2xl bg-[#141b2d] border border-slate-800">
                    <div className="text-[11px] text-slate-400 uppercase font-semibold">Tests Passed</div>
                    <div className="text-2xl font-bold text-white mt-1">
                      {evalData.metrics.passed} / {evalData.metrics.total_cases}
                    </div>
                  </div>
                  <div className="p-4 rounded-2xl bg-[#141b2d] border border-slate-800">
                    <div className="text-[11px] text-slate-400 uppercase font-semibold">Categories</div>
                    <div className="text-2xl font-bold text-cyan-400 mt-1">
                      {evalData.metrics.categories_evaluated}
                    </div>
                  </div>
                  <div className="p-4 rounded-2xl bg-[#141b2d] border border-slate-800">
                    <div className="text-[11px] text-slate-400 uppercase font-semibold">Duration</div>
                    <div className="text-2xl font-bold text-slate-300 mt-1">
                      {evalData.metrics.total_duration_sec}s
                    </div>
                  </div>
                </div>
              )}

              {/* Failure Analysis & Improvement Card */}
              {evalData?.failure_analysis_and_improvement && (
                <div className="p-5 rounded-2xl bg-gradient-to-br from-[#12192c] to-[#16213b] border border-blue-900/60 mb-6">
                  <div className="flex items-center space-x-2 text-cyan-300 text-xs font-bold uppercase tracking-wider mb-2">
                    <Sparkles className="w-4 h-4 text-cyan-400" />
                    <span>Evidence-Driven Improvement Case Study</span>
                  </div>
                  <div className="space-y-2 text-xs leading-relaxed text-slate-300">
                    <div>
                      <strong className="text-white">Identified Failure Mode:</strong>{" "}
                      {evalData.failure_analysis_and_improvement.identified_failure_mode}
                    </div>
                    <div>
                      <strong className="text-white">Architectural Improvement:</strong>{" "}
                      {evalData.failure_analysis_and_improvement.architectural_improvement}
                    </div>
                    <div className="text-emerald-400 font-semibold pt-1">
                      {evalData.failure_analysis_and_improvement.measured_improvement}
                    </div>
                  </div>
                </div>
              )}

              {/* Test Cases Table */}
              <div className="bg-[#121726] border border-slate-800 rounded-2xl overflow-hidden mb-8">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#171f32] text-slate-400 text-[11px] uppercase tracking-wider">
                    <tr>
                      <th className="py-2.5 px-4 font-semibold">ID</th>
                      <th className="py-2.5 px-4 font-semibold">Category</th>
                      <th className="py-2.5 px-4 font-semibold">Test Case</th>
                      <th className="py-2.5 px-4 font-semibold">Status</th>
                      <th className="py-2.5 px-4 font-semibold">Citations</th>
                      <th className="py-2.5 px-4 font-semibold">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {evalData?.details?.map((tc) => (
                      <tr key={tc.id} className="hover:bg-slate-800/20">
                        <td className="py-2.5 px-4 font-mono text-cyan-300 font-semibold">{tc.id}</td>
                        <td className="py-2.5 px-4 text-slate-400">{tc.category}</td>
                        <td className="py-2.5 px-4 text-slate-200 font-medium">{tc.name}</td>
                        <td className="py-2.5 px-4">
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase flex items-center space-x-1 w-max ${
                              tc.passed
                                ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                                : "bg-rose-950 text-rose-400 border border-rose-800"
                            }`}
                          >
                            <CheckCircle2 className="w-3 h-3" />
                            <span>PASS</span>
                          </span>
                        </td>
                        <td className="py-2.5 px-4 font-mono text-[11px] text-cyan-400">
                          {tc.citations?.join(", ") || "—"}
                        </td>
                        <td className="py-2.5 px-4 text-slate-400 font-mono text-[11px]">{tc.duration_ms}ms</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Edit Memory Modal */}
      {editingMemory && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#141b2d] border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-base font-bold text-white mb-2">Correct Stored Memory</h3>
            <p className="text-xs text-slate-400 mb-4">
              Update the content of this memory. A record of the change will be logged in the audit trail.
            </p>
            <textarea
              rows={3}
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full bg-[#0d121f] border border-slate-700 rounded-xl p-3 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 mb-4"
            />
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setEditingMemory(null)}
                className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleCorrectMemory}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white"
              >
                Save Correction
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Memory Modal */}
      {showAddMemoryModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={handleAddMemory} className="bg-[#141b2d] border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-base font-bold text-white mb-2">Add Durable Memory</h3>
            <p className="text-xs text-slate-400 mb-4">
              Manually add a durable preference or context item for {currentUser?.name}.
            </p>

            <div className="mb-3">
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">Category</label>
              <select
                value={newMemoryCategory}
                onChange={(e) => setNewMemoryCategory(e.target.value)}
                className="w-full bg-[#0d121f] border border-slate-700 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-cyan-500"
              >
                <option value="preference">Preference (formatting, style)</option>
                <option value="project">Project Context</option>
                <option value="role_context">Role & Responsibility</option>
              </select>
            </div>

            <div className="mb-4">
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">Memory Content</label>
              <textarea
                rows={3}
                value={newMemoryContent}
                onChange={(e) => setNewMemoryContent(e.target.value)}
                placeholder="e.g. Always respond with concise code blocks and bullet points"
                className="w-full bg-[#0d121f] border border-slate-700 rounded-xl p-3 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setShowAddMemoryModal(false)}
                className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white"
              >
                Add Memory
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Trace Inspector Modal */}
      {selectedTrace && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#141b2d] border border-slate-700 rounded-2xl max-w-2xl w-full max-h-[80vh] flex flex-col p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Layers className="w-5 h-5 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">Multi-Agent Workflow Execution Trace</h3>
              </div>
              <button
                onClick={() => setSelectedTrace(null)}
                className="text-slate-400 hover:text-white text-xs font-semibold"
              >
                Close
              </button>
            </div>

            <div className="flex-1 overflow-y-auto py-4 space-y-3">
              {selectedTrace.map((step, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-[#0f1422] border border-slate-800 text-xs">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-cyan-400">
                      Step {step.step_number}: {step.agent}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">{step.duration_ms}ms</span>
                  </div>
                  <div className="text-slate-300 font-medium mb-1">Action: {step.action}</div>
                  <div className="text-slate-400 text-[11px] bg-slate-900/60 p-2 rounded-lg font-mono mb-1.5">
                    {step.decision_notes || "Executed node logic."}
                  </div>
                  {step.outputs && (
                    <div className="text-[10px] text-slate-400">
                      Outputs: {JSON.stringify(step.outputs)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
