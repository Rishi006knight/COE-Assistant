import React, { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { 
  RefreshCw, 
  Send, 
  Sparkles,
  Server,
  Search,
  BookOpen,
  MessageSquare
} from 'lucide-react'

export default function App() {
  const [status, setStatus] = useState({
    is_indexing: false,
    indexing_message: "Idle",
    indexing_error: null,
    stats: { total_courses: 0, total_papers: 0, total_questions: 0 }
  })
  const [courses, setCourses] = useState([])
  const [selectedCourse, setSelectedCourse] = useState('')
  const [courseSearchQuery, setCourseSearchQuery] = useState('')
  const [selectedDepartment, setSelectedDepartment] = useState('All')
  const [portionQuery, setPortionQuery] = useState('')
  const [isCoursesExpanded, setIsCoursesExpanded] = useState(false)
  
  // Chat History: array of { id, sender: 'user'|'ai', text: string, provider?: string, timestamp: string }
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const pollingRef = useRef(null)
  const chatStreamEndRef = useRef(null)

  // Scroll to bottom of chat when new message arrives
  useEffect(() => {
    chatStreamEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Fetch status & stats
  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status')
      const data = await res.json()
      setStatus(data)
      
      if (data.is_indexing) {
        if (!pollingRef.current) {
          pollingRef.current = setInterval(fetchStatus, 3000)
        }
      } else {
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
          fetchCourses()
        }
      }
    } catch (err) {
      console.error("Error fetching status:", err)
    }
  }

  // Fetch courses
  const fetchCourses = async () => {
    try {
      const res = await fetch('/api/courses')
      const data = await res.json()
      setCourses(data.courses || [])
    } catch (err) {
      console.error("Error fetching courses:", err)
    }
  }

  // Trigger indexing
  const handleReindex = async () => {
    if (status.is_indexing) return
    try {
      const res = await fetch('/api/ingest', { method: 'POST' })
      const data = await res.json()
      if (data.status === 'started') {
        setStatus(prev => ({
          ...prev,
          is_indexing: true,
          indexing_message: "Scanning started..."
        }))
        if (!pollingRef.current) {
          pollingRef.current = setInterval(fetchStatus, 2000)
        }
      }
    } catch (err) {
      console.error("Error triggering indexing:", err)
    }
  }

  // Submit Question Query to AI Agent
  const handleQuerySubmit = async (e) => {
    if (e) e.preventDefault()
    const queryText = portionQuery.trim()
    if (!queryText) {
      setError("Please enter your question or query.")
      return
    }
    
    // Add user message to stream
    const userMsgId = Date.now()
    const userMessage = {
      id: userMsgId,
      sender: 'user',
      text: queryText,
      courseContext: selectedCourse,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    
    setMessages(prev => [...prev, userMessage])
    setPortionQuery('')
    setIsLoading(true)
    setError(null)

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          course_code: selectedCourse || null,
          portion_query: queryText
        })
      })
      
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || "Failed to analyze questions.")
      }

      const data = await res.json()
      
      // Add AI response to stream
      const aiMessage = {
        id: Date.now() + 1,
        sender: 'ai',
        text: data.analysis,
        provider: data.provider,
        courseName: data.course_name,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
      setMessages(prev => [...prev, aiMessage])
    } catch (err) {
      setError(err.message)
      const errorMsg = {
        id: Date.now() + 1,
        sender: 'ai',
        text: `⚠️ **Error occurred**: ${err.message}`,
        provider: 'System',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
    }
  }

  // Initial load
  useEffect(() => {
    fetchStatus()
    fetchCourses()
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [])

  // Quick preset queries helper
  const applyPreset = (text) => {
    setPortionQuery(text)
  }

  // 24 Ambient Background Floating Particles
  const ambientParticles = [
    { top: '12%', left: '8%', size: 3, type: 'teal', dx: 30, dy: -60, dur: 22 },
    { top: '25%', left: '22%', size: 2, type: 'emerald', dx: -40, dy: -80, dur: 28 },
    { top: '18%', left: '45%', size: 8, type: 'plus', dx: 25, dy: -50, dur: 25 },
    { top: '35%', left: '78%', size: 3, type: 'teal', dx: -50, dy: -70, dur: 19 },
    { top: '55%', left: '15%', size: 2, type: 'emerald', dx: 35, dy: -90, dur: 24 },
    { top: '70%', left: '32%', size: 3, type: 'teal', dx: -30, dy: -60, dur: 26 },
    { top: '65%', left: '60%', size: 8, type: 'plus', dx: 45, dy: -75, dur: 21 },
    { top: '80%', left: '85%', size: 2, type: 'emerald', dx: -25, dy: -65, dur: 27 },
    { top: '42%', left: '92%', size: 3, type: 'teal', dx: 20, dy: -80, dur: 23 },
    { top: '10%', left: '70%', size: 2, type: 'emerald', dx: -35, dy: -55, dur: 30 },
    { top: '88%', left: '18%', size: 8, type: 'plus', dx: 30, dy: -70, dur: 18 },
    { top: '5%', left: '35%', size: 3, type: 'teal', dx: -20, dy: -60, dur: 29 }
  ]

  // Filter courses by department and search
  const filteredCourses = courses.filter(c => {
    const matchesDept = selectedDepartment === 'All' || c.department === selectedDepartment
    const matchesSearch = 
      c.course_code.toLowerCase().includes(courseSearchQuery.toLowerCase()) || 
      c.course_name.toLowerCase().includes(courseSearchQuery.toLowerCase())
    return matchesDept && matchesSearch
  })

  // Selected course helper name
  const currentCourseObj = courses.find(c => c.course_code === selectedCourse)

  return (
    <div className="app-container">
      {/* Layer 2: Ambient Glowing Blobs */}
      <div className="ambient-blob ambient-blob-1"></div>
      <div className="ambient-blob ambient-blob-2"></div>

      {/* Layer 3: Ambient LED Particles */}
      <div className="particles-container">
        {ambientParticles.map((p, idx) => (
          <div 
            key={idx}
            className={`ambient-particle ${p.type}`}
            style={{
              top: p.top,
              left: p.left,
              width: p.type === 'plus' ? 'auto' : `${p.size}px`,
              height: p.type === 'plus' ? 'auto' : `${p.size}px`,
              '--dx': `${p.dx}px`,
              '--dy': `${p.dy}px`,
              animationDuration: `${p.dur}s`
            }}
          >
            {p.type === 'plus' ? '+' : ''}
          </div>
        ))}
      </div>

      {/* Top Header */}
      <header className="top-header">
        <div className="header-brand">
          <div className="brand-icon">🎓</div>
          <div className="brand-title-wrap">
            <span className="brand-title">
              <span className="teal-accent">COE</span> Automator
            </span>
            <span className="brand-subtitle">Autonomous AI Agent Tutor</span>
          </div>
        </div>

        <div className="header-actions">
          {/* Pulsing Status Pill */}
          <div className="status-pill">
            <span className={`status-dot ${status.is_indexing ? 'indexing' : 'active'}`}></span>
            <span>{status.is_indexing ? 'Indexing...' : 'Connected'}</span>
          </div>

          {/* Re-index Ghost Button */}
          <button 
            className={`reindex-btn ${status.is_indexing ? 'spinning' : ''}`}
            onClick={handleReindex}
            title={status.is_indexing ? `Indexing: ${status.indexing_message}` : 'Scan and re-index coe materials PDFs'}
            disabled={status.is_indexing}
          >
            <RefreshCw size={17} />
          </button>
        </div>
      </header>

      {/* Main Single Page Workspace */}
      <main className="main-content">
        <div className="query-workspace">
            
            {/* Left Configuration Panel (Glass Card) */}
            <aside className="query-config-panel glass-card">
              <div className="panel-header">
                <h3 className="panel-title">
                  <Sparkles className="sparkle-icon" size={18} /> Query Configurations
                </h3>
              </div>

              {/* Department & Search Filters */}
              <div className="filter-row">
                <select
                  className="custom-select"
                  value={selectedDepartment}
                  onChange={(e) => setSelectedDepartment(e.target.value)}
                >
                  <option value="All">All Depts</option>
                  {Array.from(new Set(courses.map(c => c.department).filter(Boolean))).map((dept) => (
                    <option key={dept} value={dept}>{dept}</option>
                  ))}
                </select>

                <div className="search-input-wrap">
                  <Search className="search-icon" size={14} />
                  <input 
                    type="text"
                    className="search-input"
                    placeholder="Search courses..."
                    value={courseSearchQuery}
                    onChange={(e) => setCourseSearchQuery(e.target.value)}
                  />
                </div>
              </div>

              {/* Special Top Modes (General Chat & Syllabus Queries) */}
              <div className="mode-selectors">
                <div 
                  className={`mode-card ${selectedCourse === '' ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedCourse('')
                    setError(null)
                  }}
                >
                  <div className="mode-title">💬 General Chat</div>
                  <div className="mode-desc">Global AI tutoring without syllabus constraints</div>
                </div>

                <div 
                  className={`mode-card syllabus ${selectedCourse === 'SYLLABUS' ? 'active syllabus' : ''}`}
                  onClick={() => {
                    setSelectedCourse('SYLLABUS')
                    setError(null)
                  }}
                >
                  <div className="mode-title">📚 Syllabus Queries</div>
                  <div className="mode-desc">Query curriculum, unit topics & syllabi from official PDFs</div>
                </div>
              </div>

              {/* Active Selected Course Chip (If a course was selected from search) */}
              {selectedCourse && selectedCourse !== 'SYLLABUS' && (
                <div style={{ marginTop: '0.2rem' }}>
                  <div className="courses-grid-header" style={{ marginBottom: '0.35rem', color: 'var(--teal-light)' }}>
                    Active Subject Filter
                  </div>
                  <div className="course-pill active" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', minWidth: 0 }}>
                      <span className="pill-code">{selectedCourse}</span>
                      <div className="pill-info">
                        <span className="pill-name">{currentCourseObj?.course_name || selectedCourse}</span>
                      </div>
                    </div>
                    <button 
                      type="button" 
                      onClick={(e) => { e.stopPropagation(); setSelectedCourse(''); }}
                      title="Clear course filter"
                      style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.85rem', padding: '0.2rem 0.4rem' }}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              )}

              {/* Search-Only Course Section */}
              <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, marginTop: '0.3rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                  <span className="courses-grid-header">
                    {courseSearchQuery.trim() || selectedDepartment !== 'All'
                      ? `Matching Courses (${filteredCourses.length})` 
                      : 'Course Search'}
                  </span>
                  {!courseSearchQuery.trim() && selectedDepartment === 'All' && (
                    <button
                      type="button"
                      onClick={() => setIsCoursesExpanded(prev => !prev)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--teal-light)',
                        fontSize: '0.72rem',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.25rem'
                      }}
                    >
                      {isCoursesExpanded ? '▲ Hide All' : `▼ Browse All (${courses.length})`}
                    </button>
                  )}
                </div>

                {/* Show courses when actively searching, filtering, or explicitly expanded */}
                {(courseSearchQuery.trim() || selectedDepartment !== 'All' || isCoursesExpanded) ? (
                  <div className="courses-scroll-area">
                    {filteredCourses.length === 0 ? (
                      <div style={{ textAlign: 'center', padding: '1.5rem 0', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        No courses match "{courseSearchQuery}"
                      </div>
                    ) : (
                      filteredCourses.map((c) => (
                        <div 
                          key={c.course_code}
                          className={`course-pill ${selectedCourse === c.course_code ? 'active' : ''}`}
                          onClick={() => {
                            setSelectedCourse(c.course_code)
                            setError(null)
                          }}
                        >
                          <span className="pill-code">{c.course_code}</span>
                          <div className="pill-info">
                            <span className="pill-name" title={c.course_name}>{c.course_name}</span>
                            <span className="pill-dept">{c.department || 'Engineering'}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                ) : (
                  <div style={{
                    padding: '1.2rem 1rem',
                    textAlign: 'center',
                    background: 'rgba(255, 255, 255, 0.015)',
                    border: '1px dashed rgba(255, 255, 255, 0.06)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-muted)',
                    fontSize: '0.78rem',
                    lineHeight: 1.5,
                    marginTop: '0.2rem'
                  }}>
                    🔍 Type in search bar above to instantly find any of the {courses.length} courses
                  </div>
                )}
              </div>
            </aside>

            {/* Right Chat Area (Glass Card) */}
            <section className="chat-workspace-panel glass-card">
              
              {/* Active Context Top Bar */}
              <div className="active-context-bar">
                <div className="context-title-group">
                  {selectedCourse === 'SYLLABUS' ? (
                    <>
                      <span className="context-badge syllabus">Syllabus Mode</span>
                      <span className="context-main-name">Curriculum & Syllabus AI Assistant</span>
                    </>
                  ) : selectedCourse ? (
                    <>
                      <span className="context-badge">{selectedCourse}</span>
                      <span className="context-main-name">
                        {currentCourseObj?.course_name || selectedCourse}
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="context-badge general">General Chat</span>
                      <span className="context-main-name">Global Academic AI Tutor</span>
                    </>
                  )}
                </div>

                {messages.length > 0 && messages[messages.length - 1]?.provider && (
                  <div className="server-info-badge">
                    <Server size={12} />
                    <span>Served by: <strong>{messages[messages.length - 1].provider}</strong></span>
                  </div>
                )}
              </div>

              {/* Chat Stream Area */}
              <div className="chat-stream-container">
                {messages.length === 0 ? (
                  <div className="chat-empty-state">
                    <div className="empty-state-icon">
                      {selectedCourse === 'SYLLABUS' ? '📚' : selectedCourse ? '🎓' : '✨'}
                    </div>
                    <h3 className="empty-state-title">
                      {selectedCourse === 'SYLLABUS' 
                        ? 'Syllabus & Curriculum Assistant' 
                        : selectedCourse 
                        ? `${currentCourseObj?.course_name || selectedCourse} Tutor` 
                        : 'COE Late-Night Study Lounge'}
                    </h3>
                    <p className="empty-state-desc">
                      {selectedCourse === 'SYLLABUS'
                        ? 'Ask any question about university syllabus units, curriculum structures, or course objectives extracted from official PDF documents.'
                        : selectedCourse
                        ? 'Ask questions for this course! The AI agent will search indexed question papers, analyze repeated trends, and explain syllabus portions.'
                        : 'Ask any academic question, compare concepts, or request explanations. Select a course context or syllabus mode on the left for tailored curriculum assistance.'}
                    </p>
                  </div>
                ) : (
                  messages.map((msg) => (
                    <div key={msg.id} className={`chat-message-row ${msg.sender}`}>
                      <div className={`message-bubble ${msg.sender}`}>
                        {msg.sender === 'ai' ? (
                          <div className="markdown-body">
                            <ReactMarkdown>{msg.text}</ReactMarkdown>
                          </div>
                        ) : (
                          <div>{msg.text}</div>
                        )}
                      </div>
                    </div>
                  ))
                )}

                {/* AI Typing Indicator */}
                {isLoading && (
                  <div className="chat-message-row ai">
                    <div className="ai-typing-indicator">
                      <span className="typing-dot"></span>
                      <span className="typing-dot"></span>
                      <span className="typing-dot"></span>
                    </div>
                  </div>
                )}
                
                <div ref={chatStreamEndRef} />
              </div>

              {/* Quick Query Presets Pills */}
              <div className="presets-bar">
                {selectedCourse === 'SYLLABUS' ? (
                  <>
                    <button type="button" className="preset-chip" onClick={() => applyPreset('Show syllabus overview for Computer Science engineering R2024')}>
                      📚 Syllabus Overview for CSE R2024
                    </button>
                    <button type="button" className="preset-chip" onClick={() => applyPreset('What are the unit-wise topics for Computer Networks?')}>
                      📚 Unit topics for Computer Networks
                    </button>
                    <button type="button" className="preset-chip" onClick={() => applyPreset('Explain core concepts and topics in Unit 1 of Operating Systems')}>
                      📚 Unit 1 topics for Operating Systems
                    </button>
                  </>
                ) : selectedCourse ? (
                  <>
                    <button type="button" className="preset-chip" onClick={() => applyPreset('Identify all repeated questions in Part A & B')}>
                      📊 Repeated questions in Part A & B
                    </button>
                    <button type="button" className="preset-chip" onClick={() => applyPreset('Show unit-wise important questions')}>
                      📊 Unit-wise important questions
                    </button>
                    <button type="button" className="preset-chip" onClick={() => applyPreset('Explain the core concepts of Unit 1')}>
                      💬 Explain core concepts of Unit 1
                    </button>
                  </>
                ) : (
                  <>
                    <button type="button" className="preset-chip" onClick={() => applyPreset('Explain the difference between TCP and UDP protocols in detail.')}>
                      💬 TCP vs UDP Difference
                    </button>
                    <button type="button" className="preset-chip" onClick={() => applyPreset('What is AJAX and how does it make web pages dynamic?')}>
                      💬 How AJAX works
                    </button>
                    <button type="button" className="preset-chip" onClick={() => applyPreset('Explain how HTTP session tracking works.')}>
                      💬 HTTP Session Tracking
                    </button>
                  </>
                )}
              </div>

              {/* Chat Input Bar */}
              <form onSubmit={handleQuerySubmit} className="chat-input-bar">
                <input
                  type="text"
                  className="chat-input-field"
                  placeholder={
                    selectedCourse === 'SYLLABUS'
                      ? "Ask any syllabus query... (e.g. 'Show unit topics for CS3491')"
                      : selectedCourse
                      ? `Ask anything about ${selectedCourse}... (e.g. 'repeated questions for Unit 1')`
                      : "Ask any academic question..."
                  }
                  value={portionQuery}
                  onChange={(e) => setPortionQuery(e.target.value)}
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  className="send-btn-circle"
                  disabled={isLoading || !portionQuery.trim()}
                  title="Send Question"
                >
                  <Send size={17} />
                </button>
              </form>

            </section>
          </div>
      </main>
    </div>
  )
}
