#!/usr/bin/python
import lldb

DEBUG            = False
kHeaderSize      = 0

LAZY_COMPILE     = 'LazyCompile:'
LAZY_COMPILE_LEN = len(LAZY_COMPILE)


class Address:
    def __init__(self, inst_start, name):
        self.decimalAddress     = inst_start
        self.hexadecimalAddress = "0x%x" % inst_start
        self.name               = name

unresolvedAddress = Address(0, '')

class Addresses:
    def __init__(self):
        self._addresses = []
        self._sorted = True
    
    def __getitem__(self, key):
        return self._addresses[key]

    def push(self, val):
        self._addresses.append(val)
        self._sorted = False

    def sort(self, val):
        if self._sorted: return
        print "sorting"
        self._sorted = True

    def resolve(self, addr):
        # TODO: sort
        for a in self._addresses:
            if addr < a.decimalAddress: return a

        return unresolvedAddress


addresses = Addresses()

def jit_break (frame, bp_loc, dic):

    # kHeaderSize is a constant and evaluating expressions is expensive, so we only do it once
    global kHeaderSize
    if kHeaderSize == 0:
        kHeaderSize_var = frame.EvaluateExpression('((Code*)0x0)->instruction_start()')
        kHeaderSize = kHeaderSize_var.GetValueAsUnsigned()
        if DEBUG: print 'Determined kHeaderSize: %d' % kHeaderSize


    code_var   = frame.FindVariable('code')
    name_var   = frame.FindVariable('name')
    length_var = frame.FindVariable('length')

    length      = length_var.GetValueAsUnsigned()
    name        = "%.*s" % (length, name_var.GetSummary().strip('"'))
    code        = code_var.GetValueAsUnsigned()
    inst_start  = code + kHeaderSize
    
    if name.startswith(LAZY_COMPILE):
        name = name[LAZY_COMPILE_LEN:]

    # this prints exactly what PerfBasicLogger::LogRecordedBuffer prints omitting the instruction_size since we don't need it
    if DEBUG: print '%x %s' % (inst_start, name)

    addresses.push(Address(inst_start, name))

    return False

def jit_bt (debugger, command, result, internal_dict):
    target = debugger.GetSelectedTarget()
    process = target.GetProcess()
    thread = process.GetSelectedThread()
    frame = thread.GetSelectedFrame()
    frames = thread.get_thread_frames()

    print '* thread: #%d: tid = 0x%x, %s' % (thread.GetIndexID(), thread.GetThreadID(), frame)
    for f in frames:
        star = ' '
        if f.GetFrameID() == frame.GetFrameID(): star = '*'
        name = '%s' % f.GetFunctionName()
        if name != 'None': 
            print ' %s %s' % (star, f)
        else:
            addr = f.GetPC()
            resolved = addresses.resolve(addr)
            print '  %s %s %s' % (star, f, resolved.name)

def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('breakpoint set -name v8::internal::PerfBasicLogger::LogRecordedBuffer')
    debugger.HandleCommand('breakpoint command add -F jit.jit_break')
    debugger.HandleCommand('command script add -f jit.jit_bt jbt')
    print 'The jit resolver has been initialized and is ready for use.'


### Trouble Shooting

## slow method of determining instruction_start() -- uncomment to check against calculated one
# inst_start_var = frame.EvaluateExpression('reinterpret_cast<uint64_t>(code->instruction_start())');
# inst_start_old = int(value(inst_start_var).value, 10)
