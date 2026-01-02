'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { documentsApi } from '@/lib/api';
import Link from 'next/link';

interface Transaction {
  id: number;
  transaction_date: string;
  description: string;
  amount: number;
  balance: number | null;
  category: string;
}

interface Document {
  id: number;
  filename: string;
  status: string;
  document_type: string;
  created_at: string;
  page_count: number;
  ocr_confidence: number;
  transactions: Transaction[];
}

export default function DocumentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const documentId = params?.id as string;
  
  const [document, setDocument] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDocument();
    // Poll for updates if processing
    const interval = setInterval(() => {
      if (document?.status === 'PROCESSING' || document?.status === 'UPLOADED') {
        loadDocument();
      }
    }, 3000);
    
    return () => clearInterval(interval);
  }, [documentId]);

  const loadDocument = async () => {
    try {
      const data = await documentsApi.get(parseInt(documentId));
      setDocument(data);
      setError('');
    } catch (err: any) {
      setError('Failed to load document');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'READY':
        return 'bg-green-100 text-green-800';
      case 'PROCESSING':
      case 'OCR_COMPLETE':
        return 'bg-blue-100 text-blue-800';
      case 'ERROR':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl">Loading document...</div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-xl text-red-600 mb-4">{error || 'Document not found'}</div>
          <Link href="/dashboard" className="text-blue-600 hover:text-blue-800">
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <Link href="/dashboard" className="text-blue-600 hover:text-blue-800 flex items-center gap-2">
            ← Back to Dashboard
          </Link>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Document Info */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h1 className="text-2xl font-bold mb-4">{document.filename}</h1>
          
          <div className="grid md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-600">Status</div>
              <span className={`inline-block px-3 py-1 text-sm rounded-full mt-1 ${getStatusColor(document.status)}`}>
                {document.status}
              </span>
            </div>
            
            <div>
              <div className="text-sm text-gray-600">Type</div>
              <div className="font-semibold mt-1">
                {document.document_type?.replace('_', ' ') || 'Unknown'}
              </div>
            </div>
            
            <div>
              <div className="text-sm text-gray-600">Pages</div>
              <div className="font-semibold mt-1">{document.page_count || 0}</div>
            </div>
            
            <div>
              <div className="text-sm text-gray-600">OCR Confidence</div>
              <div className="font-semibold mt-1">{document.ocr_confidence || 0}%</div>
            </div>
          </div>

          {document.status === 'PROCESSING' && (
            <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                <div className="text-sm text-blue-700">
                  Processing document... This usually takes 30-60 seconds.
                </div>
              </div>
            </div>
          )}

          {document.status === 'ERROR' && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="text-sm text-red-700">
                Failed to process document. Please try uploading again.
              </div>
            </div>
          )}
        </div>

        {/* Transactions */}
        {document.status === 'READY' && document.transactions && document.transactions.length > 0 ? (
          <div className="bg-white rounded-lg shadow">
            <div className="p-6 border-b border-gray-200 flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold">Extracted Transactions</h2>
                <p className="text-sm text-gray-600 mt-1">
                  {document.transactions.length} transactions found
                </p>
              </div>
              <button className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-semibold">
                Sync to QuickBooks →
              </button>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Description
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Category
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Amount
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Balance
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {document.transactions.map((txn) => (
                    <tr key={txn.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {new Date(txn.transaction_date).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        {txn.description}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-800">
                          {txn.category}
                        </span>
                      </td>
                      <td className={`px-6 py-4 whitespace-nowrap text-right font-semibold ${
                        txn.amount >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {formatCurrency(txn.amount)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-500">
                        {txn.balance !== null ? formatCurrency(txn.balance) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-6 border-t border-gray-200 bg-gray-50">
              <div className="flex justify-between items-center">
                <div className="text-sm text-gray-600">
                  Review transactions and click "Sync to QuickBooks" when ready
                </div>
                <button className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition font-semibold">
                  ✓ Approve & Sync
                </button>
              </div>
            </div>
          </div>
        ) : document.status === 'READY' ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <div className="text-4xl mb-4">📄</div>
            <div className="text-lg font-semibold mb-2">No Transactions Found</div>
            <div className="text-gray-600">
              The document was processed but no transactions were extracted.
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
