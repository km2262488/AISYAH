#!/usr/bin/env python3
"""
AISYAH - Website Load Tester with Live Dashboard
Real-time monitoring with rich terminal UI - Portrait Mode
"""

import asyncio
import time
import statistics
import threading
from datetime import datetime
from collections import deque, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from queue import Queue, Empty

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.align import Align
from rich import box
from rich.text import Text
from rich.color import Color

# Try to import optional plotting library
try:
    import plotext as plt
    HAS_PLOTEXT = True
except ImportError:
    HAS_PLOTEXT = False

console = Console()

# ============================================================================
# AISYAH Banner
# ============================================================================

AISYAH_BANNER = """
═════════════════════════════════════════════════                                                   
 █████╗ ██╗███████╗██╗   ██╗ █████╗ ██╗  ██╗
██╔══██╗██║██╔════╝╚██╗ ██╔╝██╔══██╗██║  ██║
███████║██║███████╗ ╚████╔╝ ███████║███████║
██╔══██║██║╚════██║  ╚██╔╝  ██╔══██║██╔══██║
██║  ██║██║███████║   ██║   ██║  ██║██║  ██║
╚═╝  ╚═╝╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝                  
                                   Website Load Tester with Live Dashboard                     
  ═════════════════════════════════════════════════
"""

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class AisyahRequestResult:
    """Single request result"""
    request_id: int
    status_code: Optional[int]
    response_time: Optional[float]
    success: bool
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class AisyahStats:
    """Real-time statistics"""
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    status_codes: Counter = field(default_factory=Counter)
    errors: List[Dict] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful / self.total_requests) * 100
    
    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    @property
    def requests_per_second(self) -> float:
        if self.elapsed_time == 0:
            return 0.0
        return self.total_requests / self.elapsed_time
    
    @property
    def min_response_time(self) -> Optional[float]:
        return min(self.response_times) if self.response_times else None
    
    @property
    def max_response_time(self) -> Optional[float]:
        return max(self.response_times) if self.response_times else None
    
    @property
    def avg_response_time(self) -> Optional[float]:
        return statistics.mean(self.response_times) if self.response_times else None
    
    @property
    def median_response_time(self) -> Optional[float]:
        return statistics.median(self.response_times) if self.response_times else None

# ============================================================================
# AISYAH Live Dashboard - Portrait Mode
# ============================================================================

class AisyahDashboard:
    """Live dashboard for monitoring load tests - Portrait Mode"""
    
    def __init__(self):
        self.stats = AisyahStats()
        self.running = False
        self.live = None
        self._history = deque(maxlen=60)  # 60 seconds of history
        
        # Color schemes
        self.colors = {
            'success': 'green',
            'failed': 'red',
            'warning': 'yellow',
            'info': 'blue',
            'highlight': 'cyan'
        }
        
    def update(self, result: AisyahRequestResult):
        """Update statistics with new result"""
        self.stats.total_requests += 1
        
        if result.success:
            self.stats.successful += 1
            if result.response_time is not None:
                self.stats.response_times.append(result.response_time)
                self._history.append({
                    'timestamp': result.timestamp,
                    'response_time': result.response_time,
                    'status': 'success'
                })
        else:
            self.stats.failed += 1
            if result.error:
                self.stats.errors.append({
                    'id': result.request_id,
                    'error': result.error
                })
                self._history.append({
                    'timestamp': result.timestamp,
                    'response_time': 0,
                    'status': 'error'
                })
        
        if result.status_code:
            self.stats.status_codes[result.status_code] += 1
            
        self.stats.last_update = time.time()
    
    def get_status_color(self) -> str:
        """Get color based on success rate"""
        rate = self.stats.success_rate
        if rate >= 95:
            return self.colors['success']
        elif rate >= 80:
            return self.colors['warning']
        else:
            return self.colors['failed']
    
    def create_summary_panel(self) -> Panel:
        """Create summary statistics panel"""
        table = Table.grid(padding=(0, 2))
        table.add_column(justify="right", style="bold")
        table.add_column()
        
        status_color = self.get_status_color()
        elapsed = self.stats.elapsed_time
        
        table.add_row("Status", f"[{status_color}]● {'RUNNING' if self.running else 'STOPPED'}[/]")
        table.add_row("Duration", f"{self._format_time(elapsed)}")
        table.add_row("Requests", f"{self.stats.total_requests:,}")
        table.add_row("✅ Successful", f"[green]{self.stats.successful:,}[/]")
        table.add_row("❌ Failed", f"[red]{self.stats.failed:,}[/]")
        table.add_row("Success Rate", f"[{status_color}]{self.stats.success_rate:.1f}%[/]")
        table.add_row("RPS", f"{self.stats.requests_per_second:.1f}")
        
        return Panel(
            table,
            title="[bold white]📊 SUMMARY[/]",
            border_style=status_color,
            box=box.ROUNDED
        )
    
    def create_stats_panel(self) -> Panel:
        """Create statistics panel"""
        table = Table.grid(padding=(0, 2))
        table.add_column(justify="right", style="bold")
        table.add_column()
        
        # Response time stats
        table.add_row("Avg Response", f"{self._format_ms(self.stats.avg_response_time)}")
        table.add_row("Median Response", f"{self._format_ms(self.stats.median_response_time)}")
        table.add_row("Min Response", f"[green]{self._format_ms(self.stats.min_response_time)}[/]")
        table.add_row("Max Response", f"[red]{self._format_ms(self.stats.max_response_time)}[/]")
        
        # Percentiles
        if self.stats.response_times and len(self.stats.response_times) > 1:
            sorted_times = sorted(self.stats.response_times)
            p95_idx = min(int(len(sorted_times) * 0.95), len(sorted_times) - 1)
            p99_idx = min(int(len(sorted_times) * 0.99), len(sorted_times) - 1)
            table.add_row("95th Percentile", f"{sorted_times[p95_idx]:.1f} ms")
            table.add_row("99th Percentile", f"[yellow]{sorted_times[p99_idx]:.1f} ms[/]")
        
        return Panel(
            table,
            title="[bold yellow]⚡ PERFORMANCE[/]",
            border_style="yellow",
            box=box.ROUNDED
        )
    
    def create_status_codes_panel(self) -> Panel:
        """Create status codes distribution panel"""
        if not self.stats.status_codes:
            return Panel("No data yet", title="📋 Status Codes", border_style="blue")
        
        # Create table with better formatting for portrait
        table = Table.grid(padding=(0, 2))
        table.add_column(justify="right", style="bold")
        table.add_column()
        
        # Sort by count descending
        sorted_codes = sorted(self.stats.status_codes.items(), key=lambda x: x[1], reverse=True)
        
        for code, count in sorted_codes[:8]:  # Show top 8 status codes
            color = "green" if code == 200 else "yellow" if code < 400 else "red"
            pct = (count / self.stats.total_requests) * 100
            table.add_row(f"HTTP {code}", f"[{color}]{count:,} ({pct:.1f}%)[/]")
        
        # If there are more, show "others" summary
        if len(sorted_codes) > 8:
            other_count = sum(count for _, count in sorted_codes[8:])
            other_pct = (other_count / self.stats.total_requests) * 100
            table.add_row("Others", f"{other_count:,} ({other_pct:.1f}%)")
        
        return Panel(
            table,
            title="📋 Status Codes",
            border_style="blue",
            box=box.ROUNDED
        )
    
    def create_errors_panel(self) -> Panel:
        """Create errors summary panel"""
        if not self.stats.errors:
            return Panel("✅ No errors", title="Errors", border_style="green")
        
        # Show last 5 errors
        error_table = Table.grid(padding=(0, 2))
        error_table.add_column(justify="right", style="bold")
        error_table.add_column()
        
        error_counts = Counter(e['error'] for e in self.stats.errors[-10:])
        for error, count in error_counts.most_common(3):
            error_table.add_row(f"⚠ Error #{count}", f"[red]{error[:40]}...[/]")
        
        total_errors = len(self.stats.errors)
        if total_errors > 3:
            error_table.add_row("Total Errors", f"[red]{total_errors}[/]")
        
        return Panel(
            error_table,
            title=f"[red]⚠ ERRORS ({len(self.stats.errors)})[/]",
            border_style="red",
            box=box.ROUNDED
        )
    
    def create_history_chart(self) -> Panel:
        """Create response time history chart using plotext"""
        if not HAS_PLOTEXT or len(self._history) < 2:
            return Panel(
                "📈 Response time history\n(install plotext for charts)",
                title="History",
                border_style="cyan"
            )
        
        # Prepare data for plotting
        response_times = [h['response_time'] for h in self._history if h['status'] == 'success']
        
        if len(response_times) < 2:
            return Panel("Insufficient data for chart", title="History", border_style="cyan")
        
        plt.clf()
        plt.plot(response_times, color='cyan')
        plt.title(f"Response Time History - Last {len(response_times)} requests")
        plt.xlabel("Request")
        plt.ylabel("Time (ms)")
        plt.theme("dark")
        
        # Get plot as string
        plot_str = plt.build()
        
        return Panel(
            plot_str,
            title="📈 Response Time History",
            border_style="cyan",
            box=box.ROUNDED
        )
    
    def create_dashboard(self) -> Layout:
        """Create the full dashboard layout - Portrait Mode"""
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Header with AISYAH branding
        header_text = Text()
        header_text.append("🌸 AISYAH ", style="bold magenta")
        header_text.append("LIVE DASHBOARD", style="bold white")
        header_text.append(f"  {datetime.now().strftime('%H:%M:%S')}", style="dim")
        layout["header"].update(Panel(Align.center(header_text), border_style="magenta"))
        
        # Body - Vertical layout (portrait mode)
        body = Layout()
        body.split(
            Layout(name="summary", size=10),
            Layout(name="stats", size=9),
            Layout(name="status", size=7),  # Status codes moved here (below)
            Layout(name="history", size=8),
            Layout(name="errors", size=6)
        )
        
        body["summary"].update(self.create_summary_panel())
        body["stats"].update(self.create_stats_panel())
        body["status"].update(self.create_status_codes_panel())
        body["history"].update(self.create_history_chart())
        body["errors"].update(self.create_errors_panel())
        
        layout["body"].update(body)
        
        # Footer
        footer_text = Text()
        footer_text.append("🌸 AISYAH ", style="magenta")
        footer_text.append("• ", style="dim")
        footer_text.append("Press ", style="dim")
        footer_text.append("Ctrl+C", style="bold white")
        footer_text.append(" to stop", style="dim")
        layout["footer"].update(Align.center(footer_text))
        
        return layout
    
    def _format_time(self, seconds: float) -> str:
        """Format time duration"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    def _format_ms(self, value: Optional[float]) -> str:
        """Format milliseconds"""
        if value is None:
            return "N/A"
        if value < 1:
            return f"{value:.2f} ms"
        elif value < 1000:
            return f"{value:.1f} ms"
        else:
            return f"{value/1000:.2f} s"
    
    def display(self):
        """Display the dashboard in live mode"""
        with Live(self.create_dashboard(), refresh_per_second=2, console=console) as live:
            self.live = live
            while self.running or self.stats.total_requests > 0:
                if self.live:
                    self.live.update(self.create_dashboard())
                time.sleep(0.5)

# ============================================================================
# AISYAH Website Load Tester
# ============================================================================

class AisyahLoadTester:
    """Main load tester class"""
    
    def __init__(self, url: str, num_requests: int = 100, num_threads: int = 10):
        self.url = url
        self.num_requests = num_requests
        self.num_threads = num_threads
        self.dashboard = AisyahDashboard()
        self.result_queue = Queue()
        self.running = False
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AISYAH-LoadTester/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
        })
        
        # Configure timeouts
        self.session.timeout = 30
        
    def make_request(self, request_id: int) -> AisyahRequestResult:
        """Make a single HTTP request"""
        try:
            start_time = time.time()
            response = self.session.get(self.url, timeout=30)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            
            return AisyahRequestResult(
                request_id=request_id,
                status_code=response.status_code,
                response_time=response_time,
                success=response.status_code == 200
            )
        except requests.exceptions.Timeout:
            return AisyahRequestResult(
                request_id=request_id,
                status_code=None,
                response_time=None,
                success=False,
                error="Timeout"
            )
        except requests.exceptions.ConnectionError:
            return AisyahRequestResult(
                request_id=request_id,
                status_code=None,
                response_time=None,
                success=False,
                error="Connection Error"
            )
        except Exception as e:
            return AisyahRequestResult(
                request_id=request_id,
                status_code=None,
                response_time=None,
                success=False,
                error=str(e)[:100]
            )
    
    def worker(self, request_ids: List[int]):
        """Worker thread to process requests"""
        for req_id in request_ids:
            if not self.running:
                break
            result = self.make_request(req_id)
            self.result_queue.put(result)
    
    def run_test(self) -> Dict[str, Any]:
        """Run the load test with dashboard"""
        console.clear()
        
        # Show AISYAH banner
        console.print(AISYAH_BANNER, style="magenta")
        console.print()
        
        # Show test info
        info_table = Table.grid(padding=(0, 2))
        info_table.add_column(justify="right", style="bold magenta")
        info_table.add_column()
        info_table.add_row("🌐 URL", self.url)
        info_table.add_row("📊 Total Requests", f"{self.num_requests:,}")
        info_table.add_row("⚡ Threads", str(self.num_threads))
        info_table.add_row("📅 Start Time", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        console.print(Panel(info_table, title="[bold magenta]🌸 AISYAH CONFIGURATION[/]", 
                           border_style="magenta", box=box.DOUBLE))
        console.print()
        
        self.running = True
        self.dashboard.running = True
        
        # Start dashboard in separate thread
        dashboard_thread = threading.Thread(target=self.dashboard.display, daemon=True)
        dashboard_thread.start()
        
        # Process requests
        start_time = time.time()
        
        # Distribute requests among threads
        request_ids = list(range(self.num_requests))
        chunk_size = max(1, len(request_ids) // self.num_threads)
        chunks = [request_ids[i:i + chunk_size] for i in range(0, len(request_ids), chunk_size)]
        
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            # Submit work
            futures = []
            for chunk in chunks:
                future = executor.submit(self.worker, chunk)
                futures.append(future)
            
            # Process results as they come in
            completed = 0
            while completed < self.num_requests and self.running:
                try:
                    result = self.result_queue.get(timeout=0.1)
                    self.dashboard.update(result)
                    completed += 1
                except Empty:
                    continue
            
            # Wait for all futures to complete
            for future in futures:
                future.result()
        
        self.running = False
        self.dashboard.running = False
        
        # Wait for dashboard to finish
        time.sleep(1)
        
        total_time = time.time() - start_time
        
        return self.generate_report(total_time)
    
    def generate_report(self, total_time: float) -> Dict[str, Any]:
        """Generate final report"""
        stats = self.dashboard.stats
        
        report = {
            'total_requests': stats.total_requests,
            'successful': stats.successful,
            'failed': stats.failed,
            'success_rate': stats.success_rate,
            'total_time': total_time,
            'rps': stats.total_requests / total_time if total_time > 0 else 0,
            'response_times': list(stats.response_times),
            'status_codes': dict(stats.status_codes),
            'errors': stats.errors
        }
        
        # Display final summary
        console.clear()
        console.print(Panel.fit(
            "[bold magenta]🌸 AISYAH - LOAD TEST COMPLETED ✅[/]",
            border_style="magenta"
        ))
        console.print()
        
        # Summary Table
        summary_table = Table(box=box.DOUBLE, border_style="magenta")
        summary_table.add_column("Metric", style="bold magenta")
        summary_table.add_column("Value", justify="center")
        
        summary_table.add_row("Total Requests", f"{report['total_requests']:,}")
        summary_table.add_row("✅ Successful", f"[green]{report['successful']:,}[/]")
        summary_table.add_row("❌ Failed", f"[red]{report['failed']:,}[/]")
        summary_table.add_row("Success Rate", f"{report['success_rate']:.1f}%")
        summary_table.add_row("Duration", f"{total_time:.2f}s")
        summary_table.add_row("Requests/sec", f"{report['rps']:.2f}")
        
        if stats.avg_response_time:
            summary_table.add_row("Avg Response Time", f"{stats.avg_response_time:.1f} ms")
            summary_table.add_row("Max Response Time", f"[red]{stats.max_response_time:.1f} ms[/]")
            summary_table.add_row("Min Response Time", f"[green]{stats.min_response_time:.1f} ms[/]")
        
        console.print(summary_table)
        console.print()
        
        # Status codes
        if report['status_codes']:
            status_table = Table(title="Status Codes Distribution", box=box.SQUARE, border_style="blue")
            status_table.add_column("HTTP Status", justify="center", style="bold")
            status_table.add_column("Count", justify="center")
            status_table.add_column("Percentage", justify="center")
            
            for code, count in sorted(report['status_codes'].items()):
                pct = (count / report['total_requests']) * 100
                color = "green" if code == 200 else "yellow" if code < 400 else "red"
                status_table.add_row(str(code), f"[{color}]{count:,}[/]", f"{pct:.1f}%")
            
            console.print(status_table)
            console.print()
        
        # Errors
        if report['errors']:
            error_counts = Counter(e['error'] for e in report['errors'][-20:])
            error_table = Table(title="Recent Errors", box=box.SQUARE, border_style="red")
            error_table.add_column("Error Type", style="bold")
            error_table.add_column("Count", justify="center")
            
            for error, count in error_counts.most_common(10):
                error_table.add_row(error[:60] + ("..." if len(error) > 60 else ""), str(count))
            
            console.print(error_table)
            console.print()
        
        # Summary with AISYAH branding
        console.print()
        if report['success_rate'] >= 95:
            console.print("[bold magenta]🌸 AISYAH:[/] [bold green]🎯 Excellent! Website is performing well.[/]")
        elif report['success_rate'] >= 80:
            console.print("[bold magenta]🌸 AISYAH:[/] [bold yellow]⚠️ Performance could be improved.[/]")
        else:
            console.print("[bold magenta]🌸 AISYAH:[/] [bold red]❌ Website may be experiencing issues.[/]")
        
        console.print()
        console.print("[dim]🌸 AISYAH - Thank you for using![/]")
        
        return report

# ============================================================================
# Main Application
# ============================================================================

def main():
    """Main entry point for AISYAH"""
    console.clear()
    
    # Show AISYAH Banner
    console.print(AISYAH_BANNER, style="magenta")
    console.print()
    console.print(Align.center("[dim]Website Load Tester with Live Dashboard - Portrait Mode[/]"))
    console.print()
    
    # Get user input with AISYAH styling
    url = console.input("[bold magenta]🌸 AISYAH[/] [bold cyan]🌐 Enter website URL[/] (e.g., https://example.com): ").strip()
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        num_requests = console.input("[bold magenta]🌸 AISYAH[/] [bold cyan]📊 Number of requests[/] (default 100): ").strip()
        num_requests = int(num_requests) if num_requests else 100
        
        num_threads = console.input("[bold magenta]🌸 AISYAH[/] [bold cyan]⚡ Concurrent threads[/] (default 10): ").strip()
        num_threads = int(num_threads) if num_threads else 10
        
        # Validate
        num_requests = max(1, min(num_requests, 10000))
        num_threads = max(1, min(num_threads, 100))
        
    except ValueError:
        console.print("[red]⚠️ Invalid input! Using defaults.[/]")
        num_requests = 100
        num_threads = 10
    
    console.print()
    console.print("[dim]🌸 AISYAH: Starting load test... Press Ctrl+C to stop early.[/dim]")
    console.print()
    
    try:
        # Run test with AISYAH
        tester = AisyahLoadTester(url, num_requests, num_threads)
        results = tester.run_test()
        
    except KeyboardInterrupt:
        console.print("\n[bold magenta]🌸 AISYAH:[/] [yellow]⚠️ Test interrupted by user.[/]")
        if hasattr(tester, 'running'):
            tester.running = False
            tester.dashboard.running = False
        console.print("[yellow]🌸 AISYAH: Generating partial report...[/yellow]")
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold magenta]🌸 AISYAH:[/] [yellow]Test cancelled.[/]")
    except Exception as e:
        console.print(f"[bold magenta]🌸 AISYAH:[/] [red]Error: {e}[/]")
        import traceback
        console.print(traceback.format_exc())
