import React, { useState } from 'react';
import { Activity, Newspaper } from 'lucide-react';
import TaskDashboard from './TaskDashboard';
import PaperSeedView from './PaperSeedView';

export default function SourcesView({ onTriggerCompleted }) {
  const [subTab, setSubTab] = useState('tasks');

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#0b0f19]">
      {/* 顶部子导航 */}
      <div className="px-5 py-3 border-b border-[#1e2638] bg-[#111726] flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1 bg-[#161e31] p-0.5 rounded-md border border-[#1e2638] text-xs">
            <button
              onClick={() => setSubTab('tasks')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition-all font-medium ${
                subTab === 'tasks'
                  ? 'bg-[#182238] text-amber-300 border border-amber-500/30 font-semibold shadow-xs'
                  : 'text-[#94a3b8] hover:text-[#f1f5f9]'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>采集调度与管道监控</span>
            </button>

            <button
              onClick={() => setSubTab('papers')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition-all font-medium ${
                subTab === 'papers'
                  ? 'bg-[#182238] text-amber-300 border border-amber-500/30 font-semibold shadow-xs'
                  : 'text-[#94a3b8] hover:text-[#f1f5f9]'
              }`}
            >
              <Newspaper className="w-3.5 h-3.5" />
              <span>53BK 地方报纸种子库</span>
            </button>
          </div>
        </div>

        <div className="text-xs text-[#64748b] hidden sm:block">
          覆盖人民法院诉讼资产网、阿里、京东、人民法院公告网、地方报纸、中拍平台、公共资源 7 核心数据源
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-[#0b0f19]">
        <div className="max-w-6xl mx-auto">
          {subTab === 'tasks' && (
            <TaskDashboard onTriggerCompleted={onTriggerCompleted} />
          )}

          {subTab === 'papers' && (
            <PaperSeedView />
          )}
        </div>
      </div>
    </div>
  );
}
