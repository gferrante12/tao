// Do NOT change. Changes will be lost next time file is generated

#define R__DICTIONARY_FILENAME dItmpdIbdIjunodOihepdOacdOcndIel9_amd64_gcc11dIReleasedIJ25dO7dO1dItaoswdIbuilddIDataModeldIElecEventdIsrcdIWtElecEvtDict
#define R__NO_DEPRECATION

/*******************************************************************/
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define G__DICTIONARY
#include "ROOT/RConfig.hxx"
#include "TClass.h"
#include "TDictAttributeMap.h"
#include "TInterpreter.h"
#include "TROOT.h"
#include "TBuffer.h"
#include "TMemberInspector.h"
#include "TInterpreter.h"
#include "TVirtualMutex.h"
#include "TError.h"

#ifndef G__ROOT
#define G__ROOT
#endif

#include "RtypesImp.h"
#include "TIsAProxy.h"
#include "TFileMergeInfo.h"
#include <algorithm>
#include "TCollectionProxyInfo.h"
/*******************************************************************/

#include "TDataMember.h"

// Header files passed as explicit arguments
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/Event/WtElecEvt.h"

// Header files passed via #pragma extra_include

// The generated code does not explicitly qualify STL entities
namespace std {} using namespace std;

namespace ROOT {
   static void *new_TaocLcLWtElecEvt(void *p = nullptr);
   static void *newArray_TaocLcLWtElecEvt(Long_t size, void *p);
   static void delete_TaocLcLWtElecEvt(void *p);
   static void deleteArray_TaocLcLWtElecEvt(void *p);
   static void destruct_TaocLcLWtElecEvt(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const ::Tao::WtElecEvt*)
   {
      ::Tao::WtElecEvt *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TInstrumentedIsAProxy< ::Tao::WtElecEvt >(nullptr);
      static ::ROOT::TGenericClassInfo 
         instance("Tao::WtElecEvt", ::Tao::WtElecEvt::Class_Version(), "Event/WtElecEvt.h", 11,
                  typeid(::Tao::WtElecEvt), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &::Tao::WtElecEvt::Dictionary, isa_proxy, 4,
                  sizeof(::Tao::WtElecEvt) );
      instance.SetNew(&new_TaocLcLWtElecEvt);
      instance.SetNewArray(&newArray_TaocLcLWtElecEvt);
      instance.SetDelete(&delete_TaocLcLWtElecEvt);
      instance.SetDeleteArray(&deleteArray_TaocLcLWtElecEvt);
      instance.SetDestructor(&destruct_TaocLcLWtElecEvt);
      return &instance;
   }
   TGenericClassInfo *GenerateInitInstance(const ::Tao::WtElecEvt*)
   {
      return GenerateInitInstanceLocal(static_cast<::Tao::WtElecEvt*>(nullptr));
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const ::Tao::WtElecEvt*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));
} // end of namespace ROOT

namespace Tao {
//______________________________________________________________________________
atomic_TClass_ptr WtElecEvt::fgIsA(nullptr);  // static to hold class pointer

//______________________________________________________________________________
const char *WtElecEvt::Class_Name()
{
   return "Tao::WtElecEvt";
}

//______________________________________________________________________________
const char *WtElecEvt::ImplFileName()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::WtElecEvt*)nullptr)->GetImplFileName();
}

//______________________________________________________________________________
int WtElecEvt::ImplFileLine()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::WtElecEvt*)nullptr)->GetImplFileLine();
}

//______________________________________________________________________________
TClass *WtElecEvt::Dictionary()
{
   fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::WtElecEvt*)nullptr)->GetClass();
   return fgIsA;
}

//______________________________________________________________________________
TClass *WtElecEvt::Class()
{
   if (!fgIsA.load()) { R__LOCKGUARD(gInterpreterMutex); fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::WtElecEvt*)nullptr)->GetClass(); }
   return fgIsA;
}

} // namespace Tao
namespace Tao {
//______________________________________________________________________________
void WtElecEvt::Streamer(TBuffer &R__b)
{
   // Stream an object of class Tao::WtElecEvt.

   if (R__b.IsReading()) {
      R__b.ReadClassBuffer(Tao::WtElecEvt::Class(),this);
   } else {
      R__b.WriteClassBuffer(Tao::WtElecEvt::Class(),this);
   }
}

} // namespace Tao
namespace ROOT {
   // Wrappers around operator new
   static void *new_TaocLcLWtElecEvt(void *p) {
      return  p ? new(p) ::Tao::WtElecEvt : new ::Tao::WtElecEvt;
   }
   static void *newArray_TaocLcLWtElecEvt(Long_t nElements, void *p) {
      return p ? new(p) ::Tao::WtElecEvt[nElements] : new ::Tao::WtElecEvt[nElements];
   }
   // Wrapper around operator delete
   static void delete_TaocLcLWtElecEvt(void *p) {
      delete (static_cast<::Tao::WtElecEvt*>(p));
   }
   static void deleteArray_TaocLcLWtElecEvt(void *p) {
      delete [] (static_cast<::Tao::WtElecEvt*>(p));
   }
   static void destruct_TaocLcLWtElecEvt(void *p) {
      typedef ::Tao::WtElecEvt current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class ::Tao::WtElecEvt

namespace ROOT {
   static TClass *vectorlETaocLcLWtElecChannelgR_Dictionary();
   static void vectorlETaocLcLWtElecChannelgR_TClassManip(TClass*);
   static void *new_vectorlETaocLcLWtElecChannelgR(void *p = nullptr);
   static void *newArray_vectorlETaocLcLWtElecChannelgR(Long_t size, void *p);
   static void delete_vectorlETaocLcLWtElecChannelgR(void *p);
   static void deleteArray_vectorlETaocLcLWtElecChannelgR(void *p);
   static void destruct_vectorlETaocLcLWtElecChannelgR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<Tao::WtElecChannel>*)
   {
      vector<Tao::WtElecChannel> *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<Tao::WtElecChannel>));
      static ::ROOT::TGenericClassInfo 
         instance("vector<Tao::WtElecChannel>", -2, "vector", 389,
                  typeid(vector<Tao::WtElecChannel>), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlETaocLcLWtElecChannelgR_Dictionary, isa_proxy, 0,
                  sizeof(vector<Tao::WtElecChannel>) );
      instance.SetNew(&new_vectorlETaocLcLWtElecChannelgR);
      instance.SetNewArray(&newArray_vectorlETaocLcLWtElecChannelgR);
      instance.SetDelete(&delete_vectorlETaocLcLWtElecChannelgR);
      instance.SetDeleteArray(&deleteArray_vectorlETaocLcLWtElecChannelgR);
      instance.SetDestructor(&destruct_vectorlETaocLcLWtElecChannelgR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<Tao::WtElecChannel> >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<Tao::WtElecChannel>","std::vector<Tao::WtElecChannel, std::allocator<Tao::WtElecChannel> >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<Tao::WtElecChannel>*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlETaocLcLWtElecChannelgR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<Tao::WtElecChannel>*>(nullptr))->GetClass();
      vectorlETaocLcLWtElecChannelgR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlETaocLcLWtElecChannelgR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlETaocLcLWtElecChannelgR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::WtElecChannel> : new vector<Tao::WtElecChannel>;
   }
   static void *newArray_vectorlETaocLcLWtElecChannelgR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::WtElecChannel>[nElements] : new vector<Tao::WtElecChannel>[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlETaocLcLWtElecChannelgR(void *p) {
      delete (static_cast<vector<Tao::WtElecChannel>*>(p));
   }
   static void deleteArray_vectorlETaocLcLWtElecChannelgR(void *p) {
      delete [] (static_cast<vector<Tao::WtElecChannel>*>(p));
   }
   static void destruct_vectorlETaocLcLWtElecChannelgR(void *p) {
      typedef vector<Tao::WtElecChannel> current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<Tao::WtElecChannel>

namespace {
  void TriggerDictionaryInitialization_WtElecEvtDict_Impl() {
    static const char* headers[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/Event/WtElecEvt.h",
nullptr
    };
    static const char* includePaths[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Python/3.11.10/include/python3.11",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Boost/1.85.0",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/log4cpp/1.1.3/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/ROOT/6.30.08/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J24.2.0/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Geant4/10.04.p02.juno/include/geant4",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/HepMC/2.06.11/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/genie/3.04.02/include/GENIE",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/frontier/2.10.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-c/6.1.9/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-cpp/1.1.12/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libyaml/0.2.4/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime/core/session",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/nuwro/21.09.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/ElecEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.4.0/ExternalLibs/ROOT/6.30.08/include/",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/ElecEvent/",
nullptr
    };
    static const char* fwdDeclCode = R"DICTFWDDCLS(
#line 1 "WtElecEvtDict dictionary forward declarations' payload"
#pragma clang diagnostic ignored "-Wkeyword-compat"
#pragma clang diagnostic ignored "-Wignored-attributes"
#pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
extern int __Cling_AutoLoading_Map;
namespace Tao{class __attribute__((annotate("$clingAutoload$/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/Event/WtElecEvt.h")))  WtElecEvt;}
)DICTFWDDCLS";
    static const char* payloadCode = R"DICTPAYLOAD(
#line 1 "WtElecEvtDict dictionary payload"


#define _BACKWARD_BACKWARD_WARNING_H
// Inline headers
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/Event/WtElecEvt.h"

#undef  _BACKWARD_BACKWARD_WARNING_H
)DICTPAYLOAD";
    static const char* classesHeaders[] = {
"Tao::WtElecEvt", payloadCode, "@",
nullptr
};
    static bool isInitialized = false;
    if (!isInitialized) {
      TROOT::RegisterModule("WtElecEvtDict",
        headers, includePaths, payloadCode, fwdDeclCode,
        TriggerDictionaryInitialization_WtElecEvtDict_Impl, {}, classesHeaders, /*hasCxxModule*/false);
      isInitialized = true;
    }
  }
  static struct DictInit {
    DictInit() {
      TriggerDictionaryInitialization_WtElecEvtDict_Impl();
    }
  } __TheDictionaryInitializer;
}
void TriggerDictionaryInitialization_WtElecEvtDict() {
  TriggerDictionaryInitialization_WtElecEvtDict_Impl();
}
