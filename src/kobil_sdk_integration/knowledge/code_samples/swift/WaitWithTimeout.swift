// ADDITION (not from the GettingStarted): wait for the reply of one request, at most `seconds`, for tests and flows that
// must never hang. Pattern from the GettingStarted UI-test adapter (continuation resumed in the completion handler).
import Foundation
import KSMasterController

enum SdkWaitError: Swift.Error {
    case timedOut(seconds: Double)
    case unexpected(String)
}

extension MasterControllerAdapter {
    func request<Reply: KsEvent>(_ event: KSMEvent, expecting _: Reply.Type, seconds: Double = 30) async -> Result<Reply, SdkWaitError> {
        await withCheckedContinuation { (continuation: CheckedContinuation<Result<Reply, SdkWaitError>, Never>) in
            let lock = NSLock()
            var finished = false
            func finish(_ result: Result<Reply, SdkWaitError>) {
                lock.lock(); defer { lock.unlock() }
                guard !finished else { return }
                finished = true
                continuation.resume(returning: result)
            }
            DispatchQueue.global().asyncAfter(deadline: .now() + seconds) { finish(.failure(.timedOut(seconds: seconds))) }
            sendEvent2MasterController(event: event) { reply in
                if let typed = reply as? Reply {
                    finish(.success(typed))
                } else {
                    finish(.failure(.unexpected(reply.map { String(describing: type(of: $0)) } ?? "no reply")))
                }
            }
        }
    }
}
