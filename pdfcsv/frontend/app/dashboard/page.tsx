'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authApi, documentsApi } from '@/lib/api';

interface User {
  id: number;
  email: string;
  full_name?: string;
  subscription_tier: string;
  pages_processed_this_month: number;
  quickbooks_connected: boolean;
}

interface Document {
  id: number;
  filename: string;
  status: string;
  created_at: string;
  page_count: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadData();
    
    // Auto-refresh every 5 seconds to show document processing updates
    const interval = setInterval(() => {
      loadData();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [userData, docsData] = await Promise.all([
        authApi.getCurrentUser(),
        documentsApi.list()
      ]);
      setUser(userData);
      setDocuments(docsData.documents);
    } catch (error: any) {
      console.error('Failed to load data:', error);
      // Only redirect to login if it's an auth error (401)
      if (error.response?.status === 401) {
        router.push('/login');
      } else {
        // For other errors, just log and stay on page
        alert('Failed to load data. Please refresh the page.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const result = await documentsApi.upload(file);
      console.log('Upload successful:', result);
      
      // Wait a bit for the document to appear in the list
      setTimeout(async () => {
        await loadData(); // Reload documents
      }, 500);
      
      alert('Document uploaded successfully! Processing will start shortly.');
    } catch (error: any) {
      console.error('Upload failed:', error);
      alert(error.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleLogout = () => {
    authApi.logout();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-blue-600">FinFlow AI</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              {user?.email}
            </span>
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-gray-600 hover:text-gray-900"
            >
              Log Out
            </button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Stats */}
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-gray-600 mb-1">Subscription</div>
            <div className="text-2xl font-bold capitalize">
              {user?.subscription_tier}
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-gray-600 mb-1">Pages This Month</div>
            <div className="text-2xl font-bold">
              {user?.pages_processed_this_month || 0}
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-gray-600 mb-1">QuickBooks</div>
            <div className="text-2xl font-bold">
              {user?.quickbooks_connected ? (
                <span className="text-green-600">✓ Connected</span>
              ) : (
                <span className="text-gray-400">Not Connected</span>
              )}
            </div>
          </div>
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-lg shadow p-8 mb-8">
          <h2 className="text-xl font-bold mb-4">Upload Bank Statement</h2>
          
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-blue-500 transition">
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="cursor-pointer"
            >
              <div className="text-4xl mb-4">📄</div>
              <div className="text-lg font-semibold mb-2">
                {uploading ? 'Uploading...' : 'Click or drag to upload'}
              </div>
              <div className="text-sm text-gray-500">
                PDF files only • Max 10MB
              </div>
            </label>
          </div>
        </div>

        {/* Documents List */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-xl font-bold">Recent Documents</h2>
          </div>
          
          {documents.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No documents yet. Upload your first bank statement above!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Filename
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Pages
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Uploaded
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        {doc.filename}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
                          {doc.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {doc.page_count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <button
                          onClick={() => router.push(`/documents/${doc.id}`)}
                          className="text-blue-600 hover:text-blue-800 font-medium"
                        >
                          View →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
