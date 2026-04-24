import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import MeetingDetail from './pages/MeetingDetail'
import RAGSearch from './pages/RAGSearch'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/meeting/:id" element={<MeetingDetail />} />
        <Route path="/search" element={<RAGSearch />} />
      </Routes>
    </Layout>
  )
}
