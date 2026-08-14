import React, { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { 
  RefreshCw, 
  Send, 
  Sparkles,
  Server
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
  const [analysis, setAnalysis] = useState(null)
  const [providerUsed, setProviderUsed] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const pollingRef = useRef(null)

  // Fetch status & stats
  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status')
      const data = await res.json()
      setStatus(data)
      
      // If backend is currently indexing, start polling
      if (data.is_indexing) {
        if (!pollingRef.current) {
          pollingRef.current = setInterval(fetchStatus, 3000)
        }
      } else {
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
          // Refresh courses list when indexing finishes
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
        // Immediately start polling
        if (!pollingRef.current) {
          pollingRef.current = setInterval(fetchStatus, 2000)
        }
      }
    } catch (err) {
      console.error("Error triggering indexing:", err)
    }
  }

  // Submit AI Question Analysis Query
  const handleQuerySubmit = async (e) => {
    if (e) e.preventDefault()
    if (!portionQuery.trim()) {
      setError("Please enter your question/query.")
      return
    }
    
    setIsLoading(true)
    setError(null)
    setAnalysis(null)
    setProviderUsed(null)

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          course_code: selectedCourse || null,
          portion_query: portionQuery.trim()
        })
      })
      
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || "Failed to analyze questions.")
      }

      const data = await res.json()
      setAnalysis(data.analysis)
      setProviderUsed(data.provider)
    } catch (err) {
      setError(err.message)
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

  return (
    <div className="app-container">
      {/* Main Content Pane - Single Page */}
      <main className="main-content">
        {/* Top Header */}
        <header className="top-header">
          <div className="brand" style={{ marginBottom: 0 }}>
            🎓 <span className="brand-title">COE Automator</span>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 400, marginLeft: '0.5rem' }}>
              Autonomous AI Agent Tutor
            </span>
          </div>

          <div className="header-actions">
            {/* Status indicator */}
            <div className="status-badge">
              <span className={`status-dot ${status.is_indexing ? 'indexing' : 'active'}`}></span>
              <span>{status.is_indexing ? 'Indexing Folder...' : 'Connected'}</span>
            </div>

            {/* Reindex rotating icon button */}
            <button 
              className={`reindex-btn ${status.is_indexing ? 'spinning' : ''}`}
              onClick={handleReindex}
              title={status.is_indexing ? `Indexing in progress: ${status.indexing_message}` : 'Scan and re-index coe materials PDFs'}
              disabled={status.is_indexing}
            >
              <RefreshCw size={18} />
            </button>
          </div>
        </header>

        {/* Single Page Layout container */}
        <div className="view-container">
          <div className="query-workspace">
            {/* Left Configuration Panel */}
            <div className="query-config section-card">
              <h3 className="section-title">
                <Sparkles size={20} style={{ color: 'var(--secondary)' }} /> Query Configurations
              </h3>
              
              <form onSubmit={handleQuerySubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', height: '100%' }}>
                
                {/* Searchable Course Selector List */}
                <div className="form-group" style={{ display: 'flex', flexDirection: 'column', flexGrow: 1, minHeight: '180px' }}>
                  <label>Target Course Context</label>
                  
                  <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    {/* Department Selector */}
                    <select
                      className="form-control"
                      value={selectedDepartment}
                      onChange={(e) => setSelectedDepartment(e.target.value)}
                      style={{ width: '45%', padding: '0.4rem 0.6rem', fontSize: '0.82rem', height: '36px' }}
                    >
                      <option value="All">All Depts</option>
                      {Array.from(new Set(courses.map(c => c.department).filter(Boolean))).map((dept) => (
                        <option key={dept} value={dept}>{dept}</option>
                      ))}
                    </select>
                    
                    {/* Search Searchbar */}
                    <input 
                      type="text"
                      className="form-control"
                      placeholder="🔍 Search..."
                      value={courseSearchQuery}
                      onChange={(e) => setCourseSearchQuery(e.target.value)}
                      style={{ width: '55%', padding: '0.4rem 0.6rem', fontSize: '0.85rem', height: '36px' }}
                    />
                  </div>
                  
                  <div className="course-selector-list">
                    {/* General Chat option */}
                    <div 
                      className={`course-selector-item ${selectedCourse === '' ? 'active' : ''}`}
                      onClick={() => {
                        setSelectedCourse('')
                        setAnalysis(null)
                        setError(null)
                      }}
                    >
                      <div className="course-item-info">
                        <span className="course-item-name">💬 General Chat</span>
                        <span className="course-item-desc">Global AI tutoring without syllabus constraints</span>
                      </div>
                    </div>
                    
                    {/* Syllabus option */}
                    <div 
                      className={`course-selector-item ${selectedCourse === 'SYLLABUS' ? 'active' : ''}`}
                      onClick={() => {
                        setSelectedCourse('SYLLABUS')
                        setAnalysis(null)
                        setError(null)
                      }}
                    >
                      <div className="course-item-info">
                        <span className="course-item-name">📚 Syllabus Queries</span>
                        <span className="course-item-desc">Query curriculum, unit topics & syllabi from official PDFs</span>
                      </div>
                    </div>
                    
                    {/* Filtered course list */}
                    {courses
                      .filter(c => {
                        const matchesDept = selectedDepartment === 'All' || c.department === selectedDepartment;
                        const matchesSearch = 
                          c.course_code.toLowerCase().includes(courseSearchQuery.toLowerCase()) || 
                          c.course_name.toLowerCase().includes(courseSearchQuery.toLowerCase());
                        return matchesDept && matchesSearch;
                      })
                      .map((c) => (
                        <div 
                          key={c.course_code}
                          className={`course-selector-item ${selectedCourse === c.course_code ? 'active' : ''}`}
                          onClick={() => {
                            setSelectedCourse(c.course_code)
                            setAnalysis(null)
                            setError(null)
                          }}
                        >
                          <span className="course-item-code">{c.course_code}</span>
                          <div className="course-item-info">
                            <span className="course-item-name">{c.course_name}</span>
                            <span className="course-item-desc">{c.department || 'General'}</span>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>

                {/* Specific Portion input */}
                <div className="form-group">
                  <label>Your Question / Query</label>
                  <textarea 
                    className="form-control"
                    rows={5}
                    style={{ resize: 'vertical' }}
                    placeholder={
                      selectedCourse === 'SYLLABUS'
                        ? "Type your syllabus query... (e.g. 'Show unit topics for CS3491', 'What is the syllabus for Web Technology?', or 'List topics in Unit 2 of DBMS')"
                        : "Type your question... (e.g. 'Explain HTTP session tracking mechanisms', 'TCP vs UDP', or 'repeated questions for Unit 1')"
                    }
                    value={portionQuery}
                    onChange={(e) => setPortionQuery(e.target.value)}
                    required
                  />
                </div>

                {/* Portions presets */}
                <div className="form-group">
                  <label>Quick Query Presets</label>
                  <div className="preset-container">
                    {selectedCourse === 'SYLLABUS' ? (
                      <>
                        <button type="button" className="preset-btn" onClick={() => applyPreset('Show syllabus overview for Computer Science engineering R2024')}>
                          📚 Syllabus Overview for CSE R2024
                        </button>
                        <button type="button" className="preset-btn" onClick={() => applyPreset('What are the unit-wise topics for Computer Networks?')}>
                          📚 Unit topics for Computer Networks
                        </button>
                        <button type="button" className="preset-btn" onClick={() => applyPreset('Explain core concepts and topics in Unit 1 of Operating Systems')}>
                          📚 Unit 1 topics for Operating Systems
                        </button>
                      </>
                    ) : selectedCourse ? (
                      <>
                        <button type="button" className="preset-btn" onClick={() => applyPreset('Identify all repeated questions in Part A & B')}>
                          📊 Repeated questions in Part A & B
                        </button>
                        <button type="button" className="preset-btn" onClick={() => applyPreset('Show unit-wise important questions')}>
                          📊 Unit-wise important questions
                        </button>
                        <button type="button" className="preset-btn" onClick={() => applyPreset('Explain the core concepts of Unit 1')}>
                          💬 Explain core concepts of Unit 1
                        </button>
                      </>
                    ) : (
                      <>
                        <button type="button" className="preset-btn" onClick={() => applyPreset('Explain the difference between TCP and UDP protocols in detail.')}>
                          💬 TCP vs UDP Difference
                        </button>
                        <button type="button" className="preset-btn" onClick={() => applyPreset('What is AJAX and how does it make web pages dynamic?')}>
                          💬 How AJAX works
                        </button>
                        <button type="button" className="preset-btn" onClick={() => applyPreset('Explain how HTTP session tracking works.')}>
                          💬 HTTP Session Tracking
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Submit Button */}
                <button 
                  type="submit" 
                  className="submit-btn"
                  disabled={isLoading || !portionQuery.trim()}
                >
                  <Send size={16} />
                  {isLoading ? 'Generating Answer...' : 'Ask AI Agent'}
                </button>

              </form>
            </div>

            {/* Right Output Console */}
            <div className="query-output">
              
              {/* Active Chat Context Header */}
              <div className="active-context-header">
                <div className="active-context-title">
                  {selectedCourse === 'SYLLABUS' ? (
                    <>
                      <span className="active-context-badge syllabus">Syllabus Mode</span>
                      <span>Curriculum & Syllabus AI Assistant</span>
                    </>
                  ) : selectedCourse ? (
                    <>
                      <span className="active-context-badge">{selectedCourse}</span>
                      <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '300px' }}>
                        {courses.find(c => c.course_code === selectedCourse)?.course_name}
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="active-context-badge general">General Chat</span>
                      <span>Global Academic AI Assistant</span>
                    </>
                  )}
                </div>
                
                {providerUsed && (
                  <div className="provider-info" style={{ margin: 0 }}>
                    <Server size={12} style={{ marginRight: '4px' }} /> Served by: <strong>{providerUsed}</strong>
                  </div>
                )}
              </div>

              <div className="output-console">
                {isLoading && (
                  <div className="loader-container">
                    <div className="spinner"></div>
                    <p style={{ fontWeight: 500 }}>Scanning indexed PDFs and running trend analysis...</p>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                      This involves matching historical questions to portions and identifying repetitions.
                    </p>
                  </div>
                )}

                {!isLoading && error && (
                  <div style={{ color: 'var(--danger)', padding: '1rem', border: '1px solid var(--danger)', borderRadius: '8px', backgroundColor: 'rgba(239, 68, 68, 0.05)' }}>
                    <h4 style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>Error Occurred</h4>
                    <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>{error}</p>
                  </div>
                )}

                {!isLoading && !analysis && !error && (
                  <div className="output-placeholder">
                    <div className="output-placeholder-icon">
                      {selectedCourse === 'SYLLABUS' ? '📚' : '🤖'}
                    </div>
                    <h3>
                      {selectedCourse === 'SYLLABUS' ? 'Syllabus AI Agent Workspace' : 'AI Agent Tutor Workspace'}
                    </h3>
                    <p style={{ maxWidth: '400px', fontSize: '0.9rem' }}>
                      {selectedCourse === 'SYLLABUS'
                        ? "Ask any curriculum or syllabus related question on the left. The AI will search official Curriculum & Syllabus PDFs to provide exact unit breakdowns, topic details, and course objectives."
                        : "Ask any academic question on the left. If you select a course context, the AI will use the curriculum syllabus and previous years' question papers to answer your query. If you choose General Chat, the AI will act as a general tutor and answer directly!"}
                    </p>
                  </div>
                )}

                {!isLoading && analysis && (
                  <div className="markdown-body">
                    <ReactMarkdown>{analysis}</ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
