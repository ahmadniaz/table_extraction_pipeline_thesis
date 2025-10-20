'use client';

import React from 'react';
import { 
  FileText, 
  Table, 
  BarChart3, 
  Brain, 
  Zap, 
  Shield, 
  CheckCircle, 
  ArrowRight,
  Sparkles,
  Database,
  Edit3,
  TrendingUp
} from 'lucide-react';

export default function SystemCapabilitiesPanel() {
  const capabilities = [
    {
      icon: FileText,
      title: "PDF to Excel Conversion",
      description: "Transform PDF statements into editable Excel spreadsheets with AI precision",
      color: "from-blue-500 to-cyan-500",
      bgColor: "bg-blue-50",
      iconColor: "text-blue-600"
    },
    {
      icon: Table,
      title: "Smart Table Extraction",
      description: "Automatically detect and extract tables from complex documents",
      color: "from-emerald-500 to-teal-500",
      bgColor: "bg-emerald-50",
      iconColor: "text-emerald-600"
    },
    {
      icon: Edit3,
      title: "Interactive Table Editor",
      description: "Edit, modify, and clean your data with our intuitive table editor",
      color: "from-purple-500 to-pink-500",
      bgColor: "bg-purple-50",
      iconColor: "text-purple-600"
    },
    {
      icon: BarChart3,
      title: "Advanced Analytics",
      description: "Generate comprehensive statistics and insights from your data",
      color: "from-orange-500 to-red-500",
      bgColor: "bg-orange-50",
      iconColor: "text-orange-600"
    }
  ];

  const features = [
    {
      icon: Brain,
      title: "AI-Powered Processing",
      description: "Advanced machine learning algorithms for accurate data extraction"
    },
    {
      icon: Zap,
      title: "Real-time Processing",
      description: "Fast and efficient document processing in seconds"
    },
    {
      icon: Shield,
      title: "Secure & Compliant",
      description: "Enterprise-grade security with data encryption and compliance"
    }
  ];

  return (
    <div className="bg-card rounded-2xl border border-border shadow-lg p-6 h-full">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
          <Sparkles className="h-8 w-8 text-white" />
        </div>
        <h3 className="text-2xl font-bold text-foreground mb-2">System Capabilities</h3>
        <p className="text-muted-foreground text-sm">
          Powerful AI-driven document processing and analysis
        </p>
      </div>

      {/* Additional Features */}
      <div className="space-y-3 mb-6">
        <h4 className="text-lg font-semibold text-foreground mb-3 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          Key Benefits
        </h4>
        {features.map((feature, index) => {
          const Icon = feature.icon;
          return (
            <div key={index} className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
              <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                <Icon className="h-4 w-4 text-primary" />
              </div>
              <div className="flex-1">
                <h6 className="font-medium text-foreground text-sm">{feature.title}</h6>
                <p className="text-muted-foreground text-xs">{feature.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
