import React, { useState } from 'react';
import axios from 'axios';
import { GoogleLogin } from '@react-oauth/google';
import { jwtDecode } from "jwt-decode";
import './App.css';

function App() {
  const [interests, setInterests] = useState('');
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);

  const [user, setUser] = useState(null);

  const handleLoginSuccess = (credentialResponse) => {
    const decoded = jwtDecode(credentialResponse.credential);
    console.log('User:', decoded);
    setUser(decoded);
  };

  const handleLogout = () => {
    setUser(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!interests.trim()) {
      setError('Please enter your interests');
      return;
    }

    setLoading(true);
    setError(null);
    setProfile(null);

    try {
      const response = await axios.post('http://localhost:8000/generate-profile', {
        interests: interests.trim(),
        num_recommendations: 15
      });

      setProfile(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate profile. Make sure the backend is running and OPENAI_API_KEY is set.');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Group courses by required/depth/other
  const groupCourses = () => {
    if (!profile || !profile.courses) return null;

    const required = [];
    const depthCourses = {};
    const otherCourses = {};

    profile.courses.forEach(course => {
      // ECE472 and Capstone are required
      if (course.course_code === 'ECE472H1' || 
          ['ECE496Y1', 'APS490Y1', 'BME498Y1'].includes(course.course_code)) {
        required.push(course);
      } else if (profile.depth_areas_selected.includes(course.area)) {
        if (!depthCourses[course.area]) depthCourses[course.area] = [];
        depthCourses[course.area].push(course);
      } else if (course.area !== -1) {
        if (!otherCourses[course.area]) otherCourses[course.area] = [];
        otherCourses[course.area].push(course);
      }
    });

    return { required, depthCourses, otherCourses };
  };

  const grouped = profile ? groupCourses() : null;

  return (
    <div className="app-container">
      {/* Authentication Section */}
      <div className="auth-wrapper">
        {user ? (
          <div className="user-profile">
            <img src={user.picture} alt="User" className="user-avatar" />
            <div className="user-info">
              <span className="user-name">{user.name}</span>
              <button onClick={handleLogout} className="logout-btn">Sign Out</button>
            </div>
          </div>
        ) : (
          <GoogleLogin
            onSuccess={handleLoginSuccess}
            onError={() => console.log('Login Failed')}
            theme="filled_black"
            shape="pill"
          />
        )}
      </div>

      {/* Header */}
      <div className="header">
        <h1>MagellanAI</h1>
        <p>Intelligent Course Planning Assistant for UofT ECE Students</p>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Input Section */}
        <div className="input-section">
          <form onSubmit={handleSubmit}>
            <div className="input-container">
              <label className="input-label">
                Tell us about your interests and goals:
              </label>
              <div className="input-wrapper">
                <textarea
                  className="interests-input"
                  placeholder="e.g., I'm interested in machine learning, artificial intelligence, and software engineering. I want to build intelligent systems and work on cutting-edge AI technologies..."
                  value={interests}
                  onChange={(e) => setInterests(e.target.value)}
                  disabled={loading}
                />
              </div>
              <button 
                type="submit" 
                className="submit-btn" 
                disabled={loading}
              >
                {loading ? 'Generating Profile...' : 'Generate My Course Profile'}
              </button>
            </div>
          </form>
        </div>

        {/* Results Section */}
        <div className="results-section">
          {loading && (
            <div className="loading">
              <div className="spinner"></div>
              <p className="loading-text">
                Analyzing your interests and generating personalized course profile...
              </p>
            </div>
          )}

          {error && (
            <div className="error-message">
              <strong>Error:</strong> {error}
            </div>
          )}

          {!loading && !error && !profile && (
            <div className="empty-state">
              <div className="empty-state-icon">💬</div>
              <p className="empty-state-text">
                Enter your interests above to generate your personalized course profile
              </p>
            </div>
          )}

          {!loading && profile && grouped && (
            <div className="profile-results">
              {/* Profile Header with Stats */}
              <div className="profile-header">
                <h2>Your Personalized Course Profile</h2>
                <div className="profile-stats">
                  <div className="stat-item">
                    <div className="stat-label">Total Credits</div>
                    <div className="stat-value">{profile.total_credits}</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-label">Semester Slots</div>
                    <div className="stat-value">
                      {profile.semester_plan ? profile.semester_plan.reduce((acc, r) => acc + (r.course_codes?.length || 0), 0) : 0}
                    </div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-label">Breadth Areas</div>
                    <div className="stat-value">{profile.kernel_areas_selected.join(', ')}</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-label">Depth Areas</div>
                    <div className="stat-value">{profile.depth_areas_selected.join(', ')}</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-label">Validation Status</div>
                    <div className="stat-value" style={{ fontSize: '1rem' }}>
                      <span className={`validation-badge ${profile.constraints_satisfied ? 'valid' : 'invalid'}`}>
                        {profile.constraints_satisfied ? 'All Constraints Met' : 'Constraints Failed'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Semester Plan Grid */}
              <SemesterPlanGrid
                semesterPlan={profile.semester_plan}
                courseNameByCode={Object.fromEntries(profile.courses.map(c => [c.course_code, c.course_name]))}
              />

              {/* Required Courses */}
              {grouped.required.length > 0 && (
                <div className="courses-section">
                  <h3 className="section-title">Required Courses</h3>
                  <div className="courses-grid">
                    {grouped.required.map((course, idx) => (
                      <CourseCard key={idx} course={course} />
                    ))}
                  </div>
                </div>
              )}

              {/* Depth Area Courses */}
              {Object.keys(grouped.depthCourses).length > 0 && (
                <div className="courses-section">
                  <h3 className="section-title">Depth Area Courses</h3>
                  {Object.entries(grouped.depthCourses).sort(([a], [b]) => a - b).map(([area, courses]) => (
                    <div key={area} style={{ marginBottom: '20px' }}>
                      <h4 style={{ marginBottom: '10px', color: '#667eea' }}>Area {area}</h4>
                      <div className="courses-grid">
                        {courses.sort((a, b) => b.kernel_course - a.kernel_course).map((course, idx) => (
                          <CourseCard key={idx} course={course} />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Other Area Courses */}
              {Object.keys(grouped.otherCourses).length > 0 && (
                <div className="courses-section">
                  <h3 className="section-title">Other Courses</h3>
                  {Object.entries(grouped.otherCourses).sort(([a], [b]) => a - b).map(([area, courses]) => (
                    <div key={area} style={{ marginBottom: '20px' }}>
                      <h4 style={{ marginBottom: '10px', color: '#764ba2' }}>Area {area}</h4>
                      <div className="courses-grid">
                        {courses.sort((a, b) => b.kernel_course - a.kernel_course).map((course, idx) => (
                          <CourseCard key={idx} course={course} />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Preferences Info */}
              {(profile.preferences_used.length > 0 || profile.preferences_skipped.length > 0) && (
                <div className="preferences-section">
                  <h3>Preference Matching</h3>
                  
                  {profile.preferences_used.length > 0 && (
                    <div style={{ marginBottom: '15px' }}>
                      <div style={{ fontSize: '0.875rem', color: '#6e6e80', marginBottom: '8px', fontWeight: '500' }}>
                        Used from your interests ({profile.preferences_used.length}):
                      </div>
                      <div className="preferences-list">
                        {profile.preferences_used.map((code, idx) => (
                          <span key={idx} className="preference-chip used">{code}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {profile.preferences_skipped.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.875rem', color: '#6e6e80', marginBottom: '8px', fontWeight: '500' }}>
                        Couldn't fit ({profile.preferences_skipped.length}):
                      </div>
                      <div className="preferences-list">
                        {profile.preferences_skipped.slice(0, 10).map((code, idx) => (
                          <span key={idx} className="preference-chip skipped">{code}</span>
                        ))}
                        {profile.preferences_skipped.length > 10 && (
                          <span className="preference-chip skipped">
                            +{profile.preferences_skipped.length - 10} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Course Card Component
function CourseCard({ course }) {
  return (
    <div className={`course-card ${course.kernel_course ? 'kernel' : ''}`}>
      <div className="course-header">
        <div className="course-code">{course.course_code}</div>
        <div className="course-badges">
          {course.kernel_course && <span className="badge kernel">Kernel</span>}
          {course.area !== -1 && <span className="badge area">Area {course.area}</span>}
          <span className="badge credits">{course.num_credits} cr</span>
        </div>
      </div>
      <div className="course-name">{course.course_name}</div>
    </div>
  );
}

function SemesterPlanGrid({ semesterPlan, courseNameByCode }) {
  if (!semesterPlan || semesterPlan.length !== 4) return null;

  const labels = ['3F', '3S', '4F', '4S'];

  // Support either format:
  //  A) semester_plan = [[{course_code,...}, ...], ...] (2D list of CourseInfo)
  //  B) semester_plan = [{term:'3F', course_codes:[...]} , ...] (rows with codes)
  const isRowObjects = !Array.isArray(semesterPlan[0]) && typeof semesterPlan[0] === 'object';

  const rows = isRowObjects
    ? labels.map((lab) => {
        const row = semesterPlan.find((r) => r.term === lab);
        const codes = row?.course_codes || [];
        return codes.map((code) => ({ course_code: code, course_name: courseNameByCode[code] || 'Name not available' }));
      })
    : semesterPlan.map((row) =>
        row.map((c) => ({ course_code: c.course_code, course_name: c.course_name || 'Name not available' }))
      );

  return (
    <div className="semester-section">
      <h3 className="section-title">Semester Plan</h3>

      <div className="semester-grid">
        {rows.map((row, rIdx) => (
          <div className="semester-row" key={labels[rIdx]}>
            <div className="semester-term">{labels[rIdx]}</div>

            <div className="semester-row-cells">
              {Array.from({ length: 5 }).map((_, cIdx) => {
                const cell = row[cIdx];
                return (
                  <div className="semester-cell" key={`${labels[rIdx]}-${cIdx}`}>
                    {cell ? (
                      <>
                        <div className="semester-code">{cell.course_code}</div>
                        <div className="semester-name">{cell.course_name}</div>
                      </>
                    ) : (
                      <div className="semester-empty">—</div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;

