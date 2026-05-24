import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ProcessFlow from './ProcessFlow'
import QuickFlowGuide from './QuickFlowGuide'

describe('ProcessFlow smoke test', () => {
  it('renders the flow title', () => {
    render(<ProcessFlow />)
    expect(screen.getByText('AI Agent 全流程協作')).toBeInTheDocument()
  })

  it('renders all 7 flow steps', () => {
    render(<ProcessFlow />)
    const steps = ['詢單接收', 'ATP/CTP 試算', 'PO→SO 轉換', '物流排程', '出貨追蹤', '發票與收款', '售後服務']
    steps.forEach(step => {
      expect(screen.getByText(step)).toBeInTheDocument()
    })
  })

  it('renders the footer description', () => {
    render(<ProcessFlow />)
    expect(screen.getByText(/五個 AI Agent 協同驅動/)).toBeInTheDocument()
  })
})

describe('QuickFlowGuide smoke test', () => {
  it('renders without crashing', () => {
    render(
      <MemoryRouter>
        <QuickFlowGuide />
      </MemoryRouter>
    )
    expect(screen.getByText(/快速開始/)).toBeInTheDocument()
  })
})