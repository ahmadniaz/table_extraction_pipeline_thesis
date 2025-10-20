import Modal from "../Modal";
import DashboardTable from "../../upload/components/DashboardTable";

type Props = {
    statement: any;
    onClose: () => void;
};

export default function StatementPreviewModal({ statement, onClose }: Props) {
    console.log('📊 StatementPreviewModal - Statement data:', {
        has_final_data: !!statement?.final_data,
        final_data_length: statement?.final_data?.length,
        has_edited_tables: !!statement?.edited_tables,
        edited_tables_length: statement?.edited_tables?.length,
        has_raw_data: !!statement?.raw_data,
        raw_data_length: statement?.raw_data?.length,
        statement
    });

    // Transform final_data to the format expected by DashboardTable
    const transformTables = (finalData: any[]) => {
        if (!finalData || !Array.isArray(finalData)) {
            console.log('❌ No final_data or not an array:', finalData);
            return [];
        }

        console.log('🔍 Processing', finalData.length, 'tables');

        return finalData.map((table, index) => {
            console.log(`🔍 Table ${index} structure:`, {
                is_array: Array.isArray(table),
                has_header: table?.header,
                has_rows: table?.rows,
                type: typeof table,
                keys: table && typeof table === 'object' ? Object.keys(table) : []
            });

            // Check if table has the expected structure
            if (table && typeof table === 'object') {
                // If it has header and rows, use as-is (without name to avoid "Unnamed Table" heading)
                if (table.header && table.rows) {
                    // Convert header to array if needed
                    const headerArray = Array.isArray(table.header) 
                        ? table.header 
                        : Object.values(table.header);
                    
                    // Convert rows to array if needed
                    let rowsArray;
                    if (Array.isArray(table.rows)) {
                        rowsArray = table.rows;
                    } else if (typeof table.rows === 'object') {
                        // If rows is an object with numeric keys, convert to array
                        rowsArray = Object.values(table.rows);
                    } else {
                        rowsArray = [];
                    }
                    
                    // Ensure each row is an array
                    const processedRows = rowsArray.map((row: any) => {
                        if (Array.isArray(row)) {
                            return row;
                        } else if (typeof row === 'object' && row !== null) {
                            // If row is an object, convert to array based on headers
                            return headerArray.map((header: any) => String(row[header] || ''));
                        } else {
                            return [];
                        }
                    });
                    
                    console.log(`✅ Table ${index} has header and rows format, ${processedRows.length} rows with ${headerArray.length} columns`);
                    return {
                        header: headerArray,
                        rows: processedRows
                        // Don't include name to avoid table heading
                    };
                }
                
                // If it's an array of objects (mapped data), convert to table format
                if (Array.isArray(table) && table.length > 0 && typeof table[0] === 'object') {
                    const firstRow = table[0];
                    const headers = Object.keys(firstRow);
                    const rows = table.map(row => headers.map(header => String(row[header] || '')));
                    console.log(`✅ Table ${index} converted from array of objects, ${rows.length} rows with ${headers.length} columns`);
                    
                    return {
                        header: headers,
                        rows: rows
                        // Don't include name to avoid table heading
                    };
                }
            }
            
            console.log(`❌ Table ${index} has unexpected format:`, table);
            return null;
        }).filter((table): table is { header: string[]; rows: string[][] } => table !== null);
    };

    // Try final_data first, then fall back to edited_tables or raw_data
    const dataToDisplay = statement.final_data || statement.edited_tables || statement.raw_data;
    const transformedTables = transformTables(dataToDisplay);
    console.log('📋 Transformed tables:', transformedTables, 'from data source:', 
        statement.final_data ? 'final_data' : statement.edited_tables ? 'edited_tables' : 'raw_data');

    return (
        <Modal onClose={onClose}>
            <div className="w-full h-full flex flex-col overflow-hidden bg-white dark:bg-slate-800">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">View Mapped Table</h2>
                            <p className="text-xs text-slate-600 dark:text-slate-400">Review processed and mapped data</p>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-hidden bg-slate-50 dark:bg-slate-900">
                    {transformedTables && transformedTables.length > 0 ? (
                        <div className="h-full overflow-auto bg-white dark:bg-slate-800">
                            <DashboardTable
                                tables={transformedTables}
                                fieldConfig={statement.field_config || []}
                                onEditMapping={() => { }}
                                readOnly
                            />
                        </div>
                    ) : (
                        <div className="text-center py-16">
                            <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-xl flex items-center justify-center mx-auto mb-4">
                                <svg className="w-8 h-8 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                            </div>
                            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">No mapped data available</h3>
                            <p className="text-slate-500 dark:text-slate-400 text-sm">This statement doesn&apos;t have any processed data yet.</p>
                        </div>
                    )}
                </div>
            </div>
        </Modal>
    );
}
