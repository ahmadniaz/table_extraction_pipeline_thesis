import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { CardLoader } from '@/app/upload/components/Loader';
import { Search, Edit, Trash2, Plus, ChevronLeft, ChevronRight } from 'lucide-react';

type Carrier = { id: string; name: string };

type Props = {
  carriers: Carrier[];
  selected: Carrier | null;
  onSelect: (c: Carrier) => void;
  loading?: boolean;
  onDelete: (ids: string[]) => void;
  deleting?: boolean;
  canSelectFiles?: boolean;
  canDeleteFiles?: boolean;
};

export default function CarrierList({ carriers, selected, onSelect, loading, onDelete, deleting, canSelectFiles = true, canDeleteFiles = true }: Props) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCarriers, setSelectedCarriers] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [carriersPerPage] = useState(10);
  const [editingCarrierId, setEditingCarrierId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [updating, setUpdating] = useState(false);

  const sortedCarriers = carriers
    .filter(carrier => carrier.name.toLowerCase().includes(searchQuery.toLowerCase()))
    .sort((a, b) => a.name.localeCompare(b.name));

  const paginatedCarriers = sortedCarriers.slice(
    (currentPage - 1) * carriersPerPage,
    currentPage * carriersPerPage
  );

  const handleCheckboxChange = (id: string) => {
    console.log('CarrierList handleCheckboxChange called:', { id, canSelectFiles, deleting });
    
    // Only block if user cannot select files, not based on deleting state
    if (!canSelectFiles) {
      console.log('Checkbox interaction blocked - user cannot select files');
      return;
    }
    
    setSelectedCarriers(prevSelected => {
      const newSelectedCarriers = new Set(prevSelected);
      if (newSelectedCarriers.has(id)) {
        newSelectedCarriers.delete(id);
        console.log('Removed carrier from selection:', id);
      } else {
        newSelectedCarriers.add(id);
        console.log('Added carrier to selection:', id);
      }
      console.log('Updated selectedCarriers:', Array.from(newSelectedCarriers));
      return newSelectedCarriers;
    });
  };

  const handleDelete = () => {
    if (selectedCarriers.size > 0) {
      onDelete(Array.from(selectedCarriers)); 
      setSelectedCarriers(new Set());
    }
  };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setCurrentPage(1); // Reset to first page when searching
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const startEdit = (carrier: Carrier) => {
    setEditingCarrierId(carrier.id);
    setEditName(carrier.name);
  };

  const cancelEdit = () => {
    setEditingCarrierId(null);
    setEditName('');
  };

  const saveEdit = async (carrier: Carrier) => {
    if (!editName.trim() || editName === carrier.name) {
      cancelEdit();
      return;
    }
    setUpdating(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/companies/${carrier.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editName }),
      });
      if (res.ok) {
        const updated = await res.json();
        // Update local state
        onSelect({ ...carrier, name: updated.name });
        setEditingCarrierId(null);
        setEditName('');
        toast.success('Carrier name updated!');
      } else {
        toast.error('Failed to update carrier name.');
      }
    } catch (e) {
      toast.error('Network error.');
    }
    setUpdating(false);
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6 relative w-full">
      {deleting && (
        <div className="absolute inset-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm flex items-center justify-center z-10 rounded-xl">
          <div className="flex items-center space-x-3">
            <div className="w-6 h-6 border-2 border-slate-200 dark:border-slate-600 border-t-blue-500 rounded-full animate-spin"></div>
            <span className="text-slate-700 dark:text-slate-300 font-medium">Deleting carriers...</span>
          </div>
        </div>
      )}
      
      {/* Enhanced Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-bold text-slate-800 dark:text-slate-200">Carriers</h3>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            {carriers.length} total carrier{carriers.length !== 1 ? 's' : ''}
          </p>
        </div>
        {canDeleteFiles && (
          <button className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg font-medium shadow-sm hover:bg-blue-600 transition-all duration-200">
            <Plus size={16} />
            Add New
          </button>
        )}
      </div>

      {/* Enhanced Search Bar */}
      <div className="relative mb-6">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-slate-400 dark:text-slate-500" />
        </div>
        <input
          type="text"
          placeholder="Search carriers..."
          value={searchQuery}
          onChange={handleSearch}
          className="w-full pl-10 pr-4 py-3 text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg border border-slate-200 dark:border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Enhanced Delete Button */}
      {selectedCarriers.size > 0 && canDeleteFiles && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Trash2 className="text-red-600 dark:text-red-400" size={20} />
              <span className="text-red-700 dark:text-red-300 font-medium">
                {selectedCarriers.size} carrier{selectedCarriers.size !== 1 ? 's' : ''} selected
              </span>
            </div>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="inline-flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-lg font-medium shadow-sm hover:bg-red-600 transition-all duration-200 disabled:opacity-50"
            >
              <Trash2 size={16} />
              {deleting ? 'Deleting...' : 'Delete Selected'}
            </button>
          </div>
        </div>
      )}

      {/* Enhanced Carrier List */}
      {loading ? (
        <CardLoader />
      ) : (
        <div className="space-y-2">
          {paginatedCarriers.map((carrier, index) => (
            <div
              key={carrier.id}
              className={`group relative p-4 rounded-xl border transition-all duration-200 ${
                selected?.id === carrier.id
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 shadow-md'
                  : 'border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700/50'
              }`}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="flex items-center gap-3">
                {canSelectFiles ? (
                  <input
                    type="checkbox"
                    checked={selectedCarriers.has(carrier.id)}
                    onChange={(e) => {
                      console.log('Carrier checkbox onChange triggered for:', carrier.id, 'checked:', e.target.checked);
                      e.stopPropagation();
                      handleCheckboxChange(carrier.id);
                    }}
                    onClick={(e) => {
                      console.log('Carrier checkbox onClick triggered for:', carrier.id, 'current checked state:', selectedCarriers.has(carrier.id));
                      e.stopPropagation();
                      // Since onChange might not be working, handle the toggle directly in onClick
                      handleCheckboxChange(carrier.id);
                    }}
                    className="w-4 h-4 text-blue-500 border-slate-300 rounded focus:ring-blue-500 cursor-pointer"
                    style={{ pointerEvents: 'auto', zIndex: 10 }}
                  />
                ) : (
                  <div className="w-4 h-4 border border-slate-300 dark:border-slate-600 rounded bg-slate-100 dark:bg-slate-700" title="Selection disabled"></div>
                )}
                
                {editingCarrierId === carrier.id ? (
                  <div className="flex-1 flex items-center gap-2">
                    <input
                      className="w-full py-2 px-3 text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg border border-slate-200 dark:border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent flex-1"
                      value={editName}
                      onChange={e => setEditName(e.target.value)}
                      disabled={updating}
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') saveEdit(carrier);
                        if (e.key === 'Escape') cancelEdit();
                      }}
                    />
                    <button
                      className="inline-flex items-center px-3 py-1 text-xs bg-emerald-500 text-white rounded-lg font-medium hover:bg-emerald-600 transition-colors disabled:opacity-50"
                      onClick={() => saveEdit(carrier)}
                      disabled={updating}
                    >
                      Save
                    </button>
                    <button
                      className="inline-flex items-center px-3 py-1 text-xs bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-300 rounded-lg font-medium hover:bg-slate-300 dark:hover:bg-slate-500 transition-colors disabled:opacity-50"
                      onClick={cancelEdit}
                      disabled={updating}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <>
                    <button
                      className={`flex-1 text-left font-medium transition-colors ${
                        selected?.id === carrier.id ? 'text-blue-600 dark:text-blue-400' : 'text-slate-800 dark:text-slate-200'
                      }`}
                      onClick={() => onSelect(carrier)}
                    >
                      {carrier.name}
                    </button>
                    
                    {canDeleteFiles && (
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          className="p-2 text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-600 rounded-lg transition-colors"
                          onClick={() => startEdit(carrier)}
                          disabled={updating}
                          title="Edit name"
                        >
                          <Edit size={14} />
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
              
              {/* Selection indicator */}
              {selected?.id === carrier.id && (
                <div className="absolute top-2 right-2 w-3 h-3 bg-blue-500 rounded-full shadow-sm"></div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Enhanced Pagination */}
      {sortedCarriers.length > carriersPerPage && (
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
          <button
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="inline-flex items-center gap-2 px-3 py-2 text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={16} />
            Prev
          </button>
          
          <span className="text-sm text-slate-600 dark:text-slate-400 font-medium">
            Page {currentPage} of {Math.ceil(sortedCarriers.length / carriersPerPage)}
          </span>
          
          <button
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === Math.ceil(sortedCarriers.length / carriersPerPage)}
            className="inline-flex items-center gap-2 px-3 py-2 text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
            <ChevronRight size={16} />
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && sortedCarriers.length === 0 && (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Search className="h-8 w-8 text-slate-400 dark:text-slate-500" />
          </div>
          <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">
            {searchQuery ? 'No carriers found' : 'No carriers yet'}
          </h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            {searchQuery 
              ? 'Try adjusting your search terms' 
              : 'Get started by adding your first carrier'
            }
          </p>
        </div>
      )}
    </div>
  );
}
