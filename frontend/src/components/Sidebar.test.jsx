import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Sidebar from '../components/Sidebar'

describe('Sidebar smoke test', () => {
  it('renders all navigation links', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar />
      </MemoryRouter>
    )

    expect(screen.getByText('OTD ERP')).toBeInTheDocument()
    expect(screen.getByText('儀表板')).toBeInTheDocument()
    expect(screen.getByText('客戶管理')).toBeInTheDocument()
    expect(screen.getByText('物料管理')).toBeInTheDocument()
    expect(screen.getByText('採購單 PO')).toBeInTheDocument()
    expect(screen.getByText('銷售單 SO')).toBeInTheDocument()
    expect(screen.getByText('物流追蹤')).toBeInTheDocument()
    expect(screen.getByText('報表匯出')).toBeInTheDocument()
  })

  it('highlights active route', () => {
    render(
      <MemoryRouter initialEntries={['/po']}>
        <Sidebar />
      </MemoryRouter>
    )

    const poLink = screen.getByText('採購單 PO')
    expect(poLink).toBeInTheDocument()
    expect(poLink.className).toContain('otd-accent')
  })
})