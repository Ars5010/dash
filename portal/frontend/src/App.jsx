import { Navigate, Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import ProtectedRoute from './components/ProtectedRoute'
import TimelinePage from './pages/TimelinePage'
import SummaryPage from './pages/SummaryPage'
import AbsencePage from './pages/AbsencePage'
import HolidaysPage from './pages/HolidaysPage'
import AdminPage from './pages/AdminPage'
import EmployeeProfilePage from './pages/EmployeeProfilePage'
import LoginPage from './pages/LoginPage'
import SetupPage from './pages/SetupPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route path="/" element={<Navigate to="/timeline" replace />} />
        <Route path="/setup" element={<SetupPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/timeline" element={<TimelinePage />} />
          <Route path="/employee/:userId" element={<EmployeeProfilePage />} />
          <Route path="/summary" element={<SummaryPage />} />
          <Route path="/absence" element={<AbsencePage />} />
          <Route path="/holidays" element={<HolidaysPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Route>
      </Route>
    </Routes>
  )
}
